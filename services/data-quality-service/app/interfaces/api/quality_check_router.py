from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.run_quality_check import QualityCheckService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyMappedStandardRecordRepository,
    SqlAlchemyMappingJobRepository,
    SqlAlchemyQualityCheckJobRepository,
    SqlAlchemyQualityCheckRuleResultRepository,
    SqlAlchemyQualityExceptionQueueRepository,
    SqlAlchemyQualityPublishedRecordRepository,
    SqlAlchemyQualityRuleRepository,
    SqlAlchemyQualityScoreConfigRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.interfaces.api.schemas import (
    ErrorResponse,
    MappingCompletedEvent,
    QualityCheckJobResponse,
    QualityCheckRuleResultResponse,
    QualityExceptionQueueItemResponse,
    QualityPublishedRecordResponse,
)

router = APIRouter(prefix="/quality-checks", tags=["UC-039 Chạy kiểm tra chất lượng dữ liệu"])


def get_service(db: Session = Depends(get_db)) -> QualityCheckService:
    return QualityCheckService(
        job_repo=SqlAlchemyQualityCheckJobRepository(db),
        rule_result_repo=SqlAlchemyQualityCheckRuleResultRepository(db),
        published_repo=SqlAlchemyQualityPublishedRecordRepository(db),
        exception_queue_repo=SqlAlchemyQualityExceptionQueueRepository(db),
        quality_rule_repo=SqlAlchemyQualityRuleRepository(db),
        score_config_repo=SqlAlchemyQualityScoreConfigRepository(db),
        standard_record_repo=SqlAlchemyMappedStandardRecordRepository(db),
        mapping_job_repo=SqlAlchemyMappingJobRepository(db),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-3: nhận sự kiện mapping.completed + chạy trọn pipeline ----------


@router.post(
    "",
    response_model=QualityCheckJobResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def receive_mapping_completed(
    payload: MappingCompletedEvent,
    service: QualityCheckService = Depends(get_service),
):
    """Nhận sự kiện `mapping.completed`: tra cứu quy tắc chất lượng (bước

    1) -> chạy quy tắc + tính điểm (bước 2) -> đạt ngưỡng thì công bố
    vào kho chuẩn hoá (bước 3a), dưới ngưỡng thì đẩy vào hàng đợi ngoại
    lệ cho Phụ trách Dữ liệu (bước 3b, UC-040 đọc tiếp)."""
    try:
        result = service.receive_and_process(
            mapping_job_id=payload.mapping_job_id,
            dataset_id=payload.dataset_id,
        )
        return QualityCheckJobResponse.from_entity(result.job)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[QualityCheckJobResponse])
def list_quality_check_jobs(
    dataset_id: Optional[int] = Query(None),
    mapping_job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    service: QualityCheckService = Depends(get_service),
):
    jobs = service.list_jobs(dataset_id=dataset_id, mapping_job_id=mapping_job_id, status=status)
    return [QualityCheckJobResponse.from_entity(j) for j in jobs]


@router.get(
    "/{quality_check_job_id}",
    response_model=QualityCheckJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_quality_check_job(
    quality_check_job_id: int, service: QualityCheckService = Depends(get_service)
):
    try:
        return QualityCheckJobResponse.from_entity(service.get(quality_check_job_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{quality_check_job_id}/rule-results",
    response_model=List[QualityCheckRuleResultResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_rule_results(
    quality_check_job_id: int, service: QualityCheckService = Depends(get_service)
):
    """Xem lại kết quả từng quy tắc (bước 2) -- lý do lô đạt/không đạt."""
    try:
        results = service.list_rule_results(quality_check_job_id)
        return [QualityCheckRuleResultResponse.from_entity(r) for r in results]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{quality_check_job_id}/published-records",
    response_model=List[QualityPublishedRecordResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_published_records(
    quality_check_job_id: int, service: QualityCheckService = Depends(get_service)
):
    """Xem lại các bản ghi đã công bố vào kho chuẩn hoá (bước 3a)."""
    try:
        records = service.list_published_records(quality_check_job_id)
        return [QualityPublishedRecordResponse.from_entity(r) for r in records]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{quality_check_job_id}/exception-items",
    response_model=List[QualityExceptionQueueItemResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_exception_items(
    quality_check_job_id: int, service: QualityCheckService = Depends(get_service)
):
    """Xem lại các dòng đã đẩy vào hàng đợi ngoại lệ của riêng lượt kiểm

    tra này (bước 3b)."""
    try:
        items = service.list_exception_items(quality_check_job_id)
        return [QualityExceptionQueueItemResponse.from_entity(i) for i in items]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/exception-queue/list", response_model=List[QualityExceptionQueueItemResponse])
def list_exception_queue(
    dataset_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="PENDING / RESOLVED"),
    service: QualityCheckService = Depends(get_service),
):
    """UC-040 bước 1 'Xem hàng đợi ngoại lệ' -- toàn bộ hàng đợi ngoại lệ

    chất lượng (mọi lượt kiểm tra), mặc định chưa xử lý (PENDING)."""
    items = service.list_exception_queue(dataset_id=dataset_id, status=status)
    return [QualityExceptionQueueItemResponse.from_entity(i) for i in items]