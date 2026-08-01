from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.parse_structured_data import StructuredParsingService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyParsedRecordRepository,
    SqlAlchemyParsingJobRepository,
    SqlAlchemyParsingRowErrorRepository,
    SqlAlchemyStgStructuredRowRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.infrastructure.file_storage import get_raw_data_storage
from app.interfaces.api.schemas import (
    ErrorResponse,
    ParsedRecordResponse,
    ParsingJobResponse,
    ParsingRequestedEvent,
    ParsingRowErrorResponse,
)

router = APIRouter(prefix="/parsing-jobs", tags=["UC-029 Phân tích dữ liệu có cấu trúc"])


def get_service(db: Session = Depends(get_db)) -> StructuredParsingService:
    return StructuredParsingService(
        job_repo=SqlAlchemyParsingJobRepository(db),
        stg_row_repo=SqlAlchemyStgStructuredRowRepository(db),
        parsed_record_repo=SqlAlchemyParsedRecordRepository(db),
        row_error_repo=SqlAlchemyParsingRowErrorRepository(db),
        file_storage=get_raw_data_storage(),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-6: nhận sự kiện parsing.requested + chạy trọn pipeline ----------


@router.post(
    "",
    response_model=ParsingJobResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
)
def receive_parsing_requested(
    payload: ParsingRequestedEvent,
    service: StructuredParsingService = Depends(get_service),
):
    """Nhận sự kiện `parsing.requested`: đọc dữ liệu thô -> stg_*, phân
    tích Excel/CSV/JSON/XML theo lược đồ, ánh xạ tên trường + ép kiểu, rồi
    kích hoạt + đẩy sự kiện `mapping.requested` (nếu có bản ghi thành công)."""
    try:
        job = service.receive_and_process(
            dataset_id=payload.dataset_id,
            raw_object_key=payload.raw_object_key,
            schema_fields=[f.model_dump() for f in payload.schema_fields],
            source_format=payload.source_format,
            field_mapping=payload.field_mapping,
            ingestion_run_id=payload.ingestion_run_id,
            data_source_id=payload.data_source_id,
        )
        return ParsingJobResponse.from_entity(job)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[ParsingJobResponse])
def list_parsing_jobs(
    dataset_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    ingestion_run_id: Optional[int] = Query(None),
    service: StructuredParsingService = Depends(get_service),
):
    jobs = service.list_jobs(dataset_id=dataset_id, status=status, ingestion_run_id=ingestion_run_id)
    return [ParsingJobResponse.from_entity(j) for j in jobs]


@router.get(
    "/{parsing_job_id}",
    response_model=ParsingJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_parsing_job(parsing_job_id: int, service: StructuredParsingService = Depends(get_service)):
    try:
        return ParsingJobResponse.from_entity(service.get(parsing_job_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{parsing_job_id}/row-errors",
    response_model=List[ParsingRowErrorResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_row_errors(parsing_job_id: int, service: StructuredParsingService = Depends(get_service)):
    try:
        errors = service.list_row_errors(parsing_job_id)
        return [ParsingRowErrorResponse.from_entity(e) for e in errors]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{parsing_job_id}/parsed-records",
    response_model=List[ParsedRecordResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_parsed_records(parsing_job_id: int, service: StructuredParsingService = Depends(get_service)):
    """Xem lại các bản ghi đã ánh xạ + ép kiểu (đầu ra bước 4, dùng cho
    UC-031 đọc tiếp sau khi nhận sự kiện `mapping.requested`)."""
    try:
        records = service.list_parsed_records(parsing_job_id)
        return [ParsedRecordResponse.from_entity(r) for r in records]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{parsing_job_id}/stg-rows",
    responses={404: {"model": ErrorResponse}},
)
def list_stg_rows(parsing_job_id: int, service: StructuredParsingService = Depends(get_service)):
    """Xem lại dữ liệu thô đã đọc vào bảng stg_* (bước 2), để đối chiếu/gỡ lỗi."""
    try:
        return service.list_stg_rows(parsing_job_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)