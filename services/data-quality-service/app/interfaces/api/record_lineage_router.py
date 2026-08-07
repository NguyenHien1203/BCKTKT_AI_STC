from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.trace_record_lineage import RecordLineageService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCuratedBatchSummaryRepository,
    SqlAlchemyCuratedDmRecordRepository,
    SqlAlchemyCuratedPublishJobRepository,
    SqlAlchemyMappedStandardRecordRepository,
    SqlAlchemyMappingJobRepository,
    SqlAlchemyMappingRejectionRepository,
    SqlAlchemyParsedRecordRepository,
    SqlAlchemyParsingJobRepository,
    SqlAlchemyParsingRowErrorRepository,
    SqlAlchemyQualityCheckJobRepository,
    SqlAlchemyQualityCheckRuleResultRepository,
    SqlAlchemyQualityExceptionQueueRepository,
    SqlAlchemyQualityPublishedRecordRepository,
    SqlAlchemyStgStructuredRowRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CuratedDmRecordResponse,
    ErrorResponse,
    LineageChainResponse,
    LineageStepDetailResponse,
)

router = APIRouter(
    prefix="/record-lineage",
    tags=["UC-045 Truy vết nguồn gốc bản ghi"],
)


def get_service(db: Session = Depends(get_db)) -> RecordLineageService:
    return RecordLineageService(
        dm_record_repo=SqlAlchemyCuratedDmRecordRepository(db),
        curated_publish_job_repo=SqlAlchemyCuratedPublishJobRepository(db),
        batch_summary_repo=SqlAlchemyCuratedBatchSummaryRepository(db),
        quality_check_job_repo=SqlAlchemyQualityCheckJobRepository(db),
        quality_rule_result_repo=SqlAlchemyQualityCheckRuleResultRepository(db),
        quality_published_repo=SqlAlchemyQualityPublishedRecordRepository(db),
        quality_exception_repo=SqlAlchemyQualityExceptionQueueRepository(db),
        mapping_job_repo=SqlAlchemyMappingJobRepository(db),
        mapping_rejection_repo=SqlAlchemyMappingRejectionRepository(db),
        mapped_record_repo=SqlAlchemyMappedStandardRecordRepository(db),
        parsing_job_repo=SqlAlchemyParsingJobRepository(db),
        stg_row_repo=SqlAlchemyStgStructuredRowRepository(db),
        parsed_record_repo=SqlAlchemyParsedRecordRepository(db),
        parsing_row_error_repo=SqlAlchemyParsingRowErrorRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: 'Chọn bản ghi curated' (xem lại 1 bản ghi cụ thể) ----------
# Danh sách để chọn dùng lại GET /curated-publish/dm-records (UC-041).


@router.get(
    "/curated-records/{curated_dm_record_id}",
    response_model=CuratedDmRecordResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_curated_record(
    curated_dm_record_id: int, service: RecordLineageService = Depends(get_service)
):
    """Bước 1 'Chọn bản ghi curated' -- xem lại thông tin 1 bản ghi cụ thể

    trước khi truy vết nguồn gốc."""
    try:
        return CuratedDmRecordResponse.from_entity(
            service.get_curated_record(curated_dm_record_id)
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: 'Xem nguồn gốc dữ liệu qua các bước' ----------


@router.get(
    "/curated-records/{curated_dm_record_id}/chain",
    response_model=LineageChainResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_lineage_chain(
    curated_dm_record_id: int, service: RecordLineageService = Depends(get_service)
):
    """Bước 2 'Xem nguồn gốc dữ liệu qua các bước (thô -> phân tích ->

    ánh xạ -> chất lượng -> công bố)' -- hệ thống hiển thị chuỗi."""
    try:
        return LineageChainResponse.from_entity(service.get_chain(curated_dm_record_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: 'Xem chi tiết từng bước' ----------


@router.get(
    "/curated-records/{curated_dm_record_id}/steps/{step}",
    response_model=LineageStepDetailResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def get_lineage_step_detail(
    curated_dm_record_id: int,
    step: str,
    service: RecordLineageService = Depends(get_service),
):
    """Bước 3 'Xem chi tiết từng bước' -- hệ thống hiển thị dữ liệu

    vào/ra + phép biến đổi của 1 bước cụ thể (RAW/PARSING/MAPPING/
    QUALITY/PUBLISH)."""
    try:
        return LineageStepDetailResponse.from_entity(
            service.get_step_detail(curated_dm_record_id, step)
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)