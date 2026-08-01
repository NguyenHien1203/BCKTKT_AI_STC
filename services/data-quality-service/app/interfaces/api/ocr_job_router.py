from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.ocr_extract_pdf import OcrExtractionService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyOcrExtractedTableRepository,
    SqlAlchemyOcrJobRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.infrastructure.file_storage import get_document_file_storage
from app.infrastructure.ocr_engine import get_ocr_engine
from app.interfaces.api.schemas import (
    ErrorResponse,
    OcrExtractedTableResponse,
    OcrJobResponse,
    OcrRequestedEvent,
)

router = APIRouter(prefix="/ocr-jobs", tags=["UC-030 Phân tích PDF/bản quét + OCR"])


def get_service(db: Session = Depends(get_db)) -> OcrExtractionService:
    return OcrExtractionService(
        job_repo=SqlAlchemyOcrJobRepository(db),
        table_repo=SqlAlchemyOcrExtractedTableRepository(db),
        file_storage=get_document_file_storage(),
        ocr_engine_factory=get_ocr_engine,
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-6: nhận sự kiện ocr.requested + chạy trọn pipeline ----------


@router.post(
    "",
    response_model=OcrJobResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
)
def receive_ocr_requested(
    payload: OcrRequestedEvent,
    service: OcrExtractionService = Depends(get_service),
):
    """Nhận sự kiện `ocr.requested`: đọc tệp PDF/bản quét (bucket
    `raw-documents`) -> chạy OCR (PaddleOCR/olmOCR) -> trích xuất văn bản
    + bảng -> lưu dữ liệu có cấu trúc -> kích hoạt + đẩy sự kiện
    `ocr.completed` + `parsing.requested` (nếu trích được nội dung)."""
    try:
        job = service.receive_and_process(
            raw_object_key=payload.raw_object_key,
            van_ban_intake_id=payload.van_ban_intake_id,
            data_source_id=payload.data_source_id,
            so_ky_hieu=payload.so_ky_hieu,
            engine=payload.engine,
        )
        return OcrJobResponse.from_entity(job)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[OcrJobResponse])
def list_ocr_jobs(
    data_source_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    van_ban_intake_id: Optional[int] = Query(None),
    service: OcrExtractionService = Depends(get_service),
):
    jobs = service.list_jobs(
        data_source_id=data_source_id, status=status, van_ban_intake_id=van_ban_intake_id
    )
    return [OcrJobResponse.from_entity(j) for j in jobs]


@router.get(
    "/{ocr_job_id}",
    response_model=OcrJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_ocr_job(ocr_job_id: int, service: OcrExtractionService = Depends(get_service)):
    try:
        return OcrJobResponse.from_entity(service.get(ocr_job_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{ocr_job_id}/tables",
    response_model=List[OcrExtractedTableResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_ocr_tables(ocr_job_id: int, service: OcrExtractionService = Depends(get_service)):
    """Xem lại các bảng trích xuất được từ tài liệu (bước 3-4)."""
    try:
        tables = service.list_tables(ocr_job_id)
        return [OcrExtractedTableResponse.from_entity(t) for t in tables]
    except DomainError as exc:
        raise _domain_error_to_http(exc)