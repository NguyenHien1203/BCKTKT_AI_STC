from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.map_field_to_standard import FieldMappingService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyMappedStandardRecordRepository,
    SqlAlchemyMappingJobRepository,
    SqlAlchemyMappingRejectionRepository,
    SqlAlchemyMappingRuleRepository,
    SqlAlchemyParsedRecordRepository,
    SqlAlchemyParsingJobRepository,
    SqlAlchemyUnmappedQueueRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    MappedStandardRecordResponse,
    MappingJobResponse,
    MappingRejectionResponse,
    MappingRequestedEvent,
    UnmappedQueueItemResponse,
)

router = APIRouter(prefix="/mapping-jobs", tags=["UC-031 Ánh xạ trường sang dạng chuẩn"])


def get_service(db: Session = Depends(get_db)) -> FieldMappingService:
    return FieldMappingService(
        mapping_job_repo=SqlAlchemyMappingJobRepository(db),
        mapping_rule_repo=SqlAlchemyMappingRuleRepository(db),
        rejection_repo=SqlAlchemyMappingRejectionRepository(db),
        unmapped_queue_repo=SqlAlchemyUnmappedQueueRepository(db),
        standard_record_repo=SqlAlchemyMappedStandardRecordRepository(db),
        parsed_record_repo=SqlAlchemyParsedRecordRepository(db),
        parsing_job_repo=SqlAlchemyParsingJobRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-3: nhận sự kiện mapping.requested + chạy trọn pipeline ----------


@router.post(
    "",
    response_model=MappingJobResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def receive_mapping_requested(
    payload: MappingRequestedEvent,
    service: FieldMappingService = Depends(get_service),
):
    """Nhận sự kiện `mapping.requested`: tra cứu quy tắc ánh xạ (có phiên
    bản) + tra cứu danh mục chuẩn -> chuẩn hoá field; từ chối trường bắt
    buộc bị NULL (ghi `mapping_rejections`); đẩy giá trị chưa ánh xạ vào
    hàng đợi cho Phụ trách Dữ liệu (`unmapped_value_queue`, UC-032 đọc
    tiếp)."""
    try:
        job = service.receive_and_process(
            parsing_job_id=payload.parsing_job_id,
            dataset_id=payload.dataset_id,
        )
        return MappingJobResponse.from_entity(job)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[MappingJobResponse])
def list_mapping_jobs(
    dataset_id: Optional[int] = Query(None),
    parsing_job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    service: FieldMappingService = Depends(get_service),
):
    jobs = service.list_jobs(dataset_id=dataset_id, parsing_job_id=parsing_job_id, status=status)
    return [MappingJobResponse.from_entity(j) for j in jobs]


@router.get(
    "/{mapping_job_id}",
    response_model=MappingJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_mapping_job(mapping_job_id: int, service: FieldMappingService = Depends(get_service)):
    try:
        return MappingJobResponse.from_entity(service.get(mapping_job_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{mapping_job_id}/rejections",
    response_model=List[MappingRejectionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_rejections(mapping_job_id: int, service: FieldMappingService = Depends(get_service)):
    """Xem lại các dòng bị từ chối vì trường bắt buộc bị NULL (bước 2)."""
    try:
        rejections = service.list_rejections(mapping_job_id)
        return [MappingRejectionResponse.from_entity(r) for r in rejections]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{mapping_job_id}/unmapped-queue",
    response_model=List[UnmappedQueueItemResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_unmapped_queue(mapping_job_id: int, service: FieldMappingService = Depends(get_service)):
    """Xem lại hàng đợi giá trị chưa ánh xạ (bước 3) -- cho Phụ trách Dữ
    liệu xử lý tiếp (UC-032)."""
    try:
        items = service.list_unmapped_queue(mapping_job_id)
        return [UnmappedQueueItemResponse.from_entity(i) for i in items]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{mapping_job_id}/standard-records",
    response_model=List[MappedStandardRecordResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_standard_records(mapping_job_id: int, service: FieldMappingService = Depends(get_service)):
    """Xem lại các bản ghi đã ánh xạ trường sang dạng chuẩn thành công."""
    try:
        records = service.list_standard_records(mapping_job_id)
        return [MappedStandardRecordResponse.from_entity(r) for r in records]
    except DomainError as exc:
        raise _domain_error_to_http(exc)