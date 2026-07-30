from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_ingestion_run import IngestionRunService
from app.application.use_cases.retry_ingestion_run import RetryIngestionRunService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDatasetRepository,
    SqlAlchemyIngestionRunRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.retry_executor import NoOpIngestionRetryExecutor
from app.interfaces.api.schemas import (
    CalendarDayResponse,
    ErrorResponse,
    IngestionRunComplete,
    IngestionRunFailureReasonResponse,
    IngestionRunListItemResponse,
    IngestionRunLogAppend,
    IngestionRunResponse,
    IngestionRunStart,
)

router = APIRouter(prefix="/ingestion-runs", tags=["UC-020 Xem lịch đầy đủ dữ liệu + lịch sử chạy"])


def get_service(db: Session = Depends(get_db)) -> IngestionRunService:
    return IngestionRunService(
        run_repo=SqlAlchemyIngestionRunRepository(db),
        dataset_repo=SqlAlchemyDatasetRepository(db),
    )


def get_retry_service(db: Session = Depends(get_db)) -> RetryIngestionRunService:
    """UC-021: Chạy lại phiên ingest lỗi. Đổi `NoOpIngestionRetryExecutor`
    thành implementation gọi Bộ điều phối thật khi tích hợp — không cần
    sửa domain/application."""
    return RetryIngestionRunService(
        run_repo=SqlAlchemyIngestionRunRepository(db),
        retry_executor=NoOpIngestionRetryExecutor(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Ghi nhận vòng đời phiên (hạ tầng dùng bởi UC-021/UC-025) ----------


@router.post(
    "",
    response_model=IngestionRunResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def start_ingestion_run(
    payload: IngestionRunStart, service: IngestionRunService = Depends(get_service)
):
    """Bắt đầu 1 phiên ingest mới: hệ thống ghi nhận vào ingestion.runs."""
    try:
        return service.start_run(
            dataset_id=payload.dataset_id,
            scheduled_task_id=payload.scheduled_task_id,
            trigger=payload.trigger,
            sync_mode=payload.sync_mode,
            started_at=payload.started_at,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{run_id}/logs",
    response_model=IngestionRunResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def append_ingestion_run_log(
    run_id: int,
    payload: IngestionRunLogAppend,
    service: IngestionRunService = Depends(get_service),
):
    """Ghi thêm 1 dòng log vào phiên đang chạy."""
    try:
        return service.append_log(
            run_id, level=payload.level, message=payload.message, timestamp=payload.timestamp
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{run_id}/complete",
    response_model=IngestionRunResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def complete_ingestion_run(
    run_id: int,
    payload: IngestionRunComplete,
    service: IngestionRunService = Depends(get_service),
):
    """Kết thúc phiên: hệ thống ghi nhận trạng thái cuối + tổng kiểm soát."""
    try:
        return service.complete_run(
            run_id,
            status=payload.status,
            records_read=payload.records_read,
            records_loaded=payload.records_loaded,
            records_failed=payload.records_failed,
            control_totals=payload.control_totals,
            error_message=payload.error_message,
            finished_at=payload.finished_at,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 1: Xem lịch sử chạy ----------


@router.get(
    "",
    response_model=List[IngestionRunListItemResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_run_history(
    dataset_id: Optional[int] = Query(None),
    scheduled_task_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO-8601, lọc theo started_at >="),
    date_to: Optional[str] = Query(None, description="ISO-8601, lọc theo started_at <="),
    service: IngestionRunService = Depends(get_service),
):
    """Xem lịch sử chạy: hệ thống truy vấn ingestion.runs và hiển thị."""
    try:
        return service.list_run_history(
            dataset_id=dataset_id,
            scheduled_task_id=scheduled_task_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Xem lịch đầy đủ dữ liệu (heatmap) ----------


@router.get(
    "/calendar",
    response_model=List[CalendarDayResponse],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def get_data_calendar(
    dataset_id: int = Query(..., gt=0),
    date_from: str = Query(..., description="Ngày bắt đầu, định dạng YYYY-MM-DD"),
    date_to: str = Query(..., description="Ngày kết thúc, định dạng YYYY-MM-DD"),
    service: IngestionRunService = Depends(get_service),
):
    """Xem lịch đầy đủ dữ liệu (kỳ thiếu dữ liệu): hệ thống hiển thị
    heatmap tổng hợp theo từng ngày."""
    try:
        return service.get_data_calendar(dataset_id, date_from=date_from, date_to=date_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Xem chi tiết phiên cụ thể ----------


@router.get(
    "/{run_id}",
    response_model=IngestionRunResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_run_detail(run_id: int, service: IngestionRunService = Depends(get_service)):
    """Xem chi tiết phiên cụ thể: hệ thống hiển thị log + tổng kiểm soát."""
    try:
        return service.get_run_detail(run_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- UC-021: Chạy lại phiên ingest lỗi ----------


@router.get(
    "/{run_id}/failure-reason",
    response_model=IngestionRunFailureReasonResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["UC-021 Chạy lại phiên ingest lỗi"],
)
def get_failure_reason(run_id: int, service: RetryIngestionRunService = Depends(get_retry_service)):
    """Bước 1: Chọn phiên bị lỗi -> hệ thống hiển thị nguyên nhân."""
    try:
        return service.get_failure_reason(run_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{run_id}/retry",
    response_model=IngestionRunResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    tags=["UC-021 Chạy lại phiên ingest lỗi"],
)
def retry_ingestion_run(run_id: int, service: RetryIngestionRunService = Depends(get_retry_service)):
    """Bước 2-4: Kích hoạt Bộ điều phối chạy lại (có khoá chống trùng) ->
    hệ thống chạy lại + ghi lịch sử -> cập nhật trạng thái vào
    ingestion.runs. Trả về phiên RETRY mới được tạo."""
    try:
        return service.retry_run(run_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{run_id}/retries",
    response_model=List[IngestionRunListItemResponse],
    responses={404: {"model": ErrorResponse}},
    tags=["UC-021 Chạy lại phiên ingest lỗi"],
)
def list_retries(run_id: int, service: RetryIngestionRunService = Depends(get_retry_service)):
    """Xem lịch sử các lượt chạy lại (RETRY) đã kích hoạt cho 1 phiên gốc."""
    try:
        return service.list_retries(run_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)