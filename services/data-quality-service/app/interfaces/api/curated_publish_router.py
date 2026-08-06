from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.publish_to_curated_store import CuratedPublishService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCuratedBatchSummaryRepository,
    SqlAlchemyCuratedDatasetFreshnessRepository,
    SqlAlchemyCuratedDmRecordRepository,
    SqlAlchemyCuratedPublishJobRepository,
    SqlAlchemyQualityCheckJobRepository,
    SqlAlchemyQualityPublishedRecordRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.interfaces.api.schemas import (
    CuratedBatchSummaryResponse,
    CuratedDatasetFreshnessResponse,
    CuratedDmRecordResponse,
    CuratedPublishJobResponse,
    CuratedPublishRequestedEvent,
    ErrorResponse,
)

router = APIRouter(
    prefix="/curated-publish",
    tags=["UC-041 Công bố vào kho chuẩn hoá + batch_summary"],
)


def get_service(db: Session = Depends(get_db)) -> CuratedPublishService:
    return CuratedPublishService(
        job_repo=SqlAlchemyCuratedPublishJobRepository(db),
        dm_record_repo=SqlAlchemyCuratedDmRecordRepository(db),
        batch_summary_repo=SqlAlchemyCuratedBatchSummaryRepository(db),
        freshness_repo=SqlAlchemyCuratedDatasetFreshnessRepository(db),
        published_record_repo=SqlAlchemyQualityPublishedRecordRepository(db),
        quality_check_job_repo=SqlAlchemyQualityCheckJobRepository(db),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-4: nhận sự kiện curated.publish.requested + chạy trọn pipeline ----------


@router.post(
    "/jobs",
    response_model=CuratedPublishJobResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def receive_curated_publish_requested(
    payload: CuratedPublishRequestedEvent,
    service: CuratedPublishService = Depends(get_service),
):
    """Nhận sự kiện `curated.publish.requested`: chèn/cập nhật vào

    `dm_*` (bước 1) -> đặt `publish_status=approved` (bước 2) -> tạo
    `batch_summary` + cập nhật độ mới dữ liệu (bước 3) -> phát sự kiện
    `curated.published` (bước 4). Trả 404 nếu `quality_check_job_id`
    không tồn tại; nếu tồn tại nhưng chưa có bản ghi nào để công bố,
    trả 201 với `status=FAILED` (không raise lỗi HTTP)."""
    try:
        result = service.receive_and_process(
            quality_check_job_id=payload.quality_check_job_id,
            dataset_id=payload.dataset_id,
            mapping_job_id=payload.mapping_job_id,
            record_count=payload.record_count,
            source=payload.source,
        )
        return CuratedPublishJobResponse.from_entity(result.job)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/jobs", response_model=List[CuratedPublishJobResponse])
def list_curated_publish_jobs(
    dataset_id: Optional[int] = Query(None),
    quality_check_job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    service: CuratedPublishService = Depends(get_service),
):
    jobs = service.list_jobs(
        dataset_id=dataset_id, quality_check_job_id=quality_check_job_id, status=status
    )
    return [CuratedPublishJobResponse.from_entity(j) for j in jobs]


@router.get(
    "/jobs/{curated_publish_job_id}",
    response_model=CuratedPublishJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_curated_publish_job(
    curated_publish_job_id: int, service: CuratedPublishService = Depends(get_service)
):
    try:
        return CuratedPublishJobResponse.from_entity(service.get(curated_publish_job_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/jobs/{curated_publish_job_id}/dm-records",
    response_model=List[CuratedDmRecordResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_dm_records_for_job(
    curated_publish_job_id: int, service: CuratedPublishService = Depends(get_service)
):
    """Xem lại các bản ghi `dm_*` đã chèn/cập nhật trong 1 lượt công bố (bước 1)."""
    try:
        records = service.list_dm_records_for_job(curated_publish_job_id)
        return [CuratedDmRecordResponse.from_entity(r) for r in records]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xem kho chuẩn hoá (dm_*), batch_summary, độ mới dữ liệu ----------


@router.get("/dm-records", response_model=List[CuratedDmRecordResponse])
def list_dm_records(
    dataset_id: Optional[int] = Query(None),
    publish_status: Optional[str] = Query(None, description="Mặc định: approved"),
    service: CuratedPublishService = Depends(get_service),
):
    """Xem toàn bộ kho chuẩn hoá (`dm_*`) -- lọc theo tập dữ liệu/`publish_status`."""
    records = service.list_dm_records(dataset_id=dataset_id, publish_status=publish_status)
    return [CuratedDmRecordResponse.from_entity(r) for r in records]


@router.get("/batch-summaries", response_model=List[CuratedBatchSummaryResponse])
def list_batch_summaries(
    dataset_id: Optional[int] = Query(None),
    quality_check_job_id: Optional[int] = Query(None),
    service: CuratedPublishService = Depends(get_service),
):
    """Bước 3 'Tạo batch_summary' -- tra cứu lại lịch sử các lượt công bố."""
    summaries = service.list_batch_summaries(
        dataset_id=dataset_id, quality_check_job_id=quality_check_job_id
    )
    return [CuratedBatchSummaryResponse.from_entity(s) for s in summaries]


@router.get("/dataset-freshness", response_model=List[CuratedDatasetFreshnessResponse])
def list_dataset_freshness(service: CuratedPublishService = Depends(get_service)):
    """Bước 3 'cập nhật độ mới dữ liệu' -- toàn bộ tập dữ liệu đã công bố."""
    items = service.list_dataset_freshness()
    return [CuratedDatasetFreshnessResponse.from_entity(f) for f in items]


@router.get(
    "/dataset-freshness/{dataset_id}",
    response_model=CuratedDatasetFreshnessResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dataset_freshness(dataset_id: int, service: CuratedPublishService = Depends(get_service)):
    """Bước 3 'cập nhật độ mới dữ liệu' -- độ mới của 1 tập dữ liệu cụ thể."""
    freshness = service.get_dataset_freshness(dataset_id)
    if freshness is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CURATED_DATASET_FRESHNESS_NOT_FOUND",
                "message": f"Tập dữ liệu id={dataset_id} chưa từng được công bố vào kho chuẩn hoá",
            },
        )
    return CuratedDatasetFreshnessResponse.from_entity(freshness)