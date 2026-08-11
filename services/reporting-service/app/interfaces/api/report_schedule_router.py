from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.generate_and_export_report import ReportGenerationService
from app.application.use_cases.manage_report_schedule import ReportScheduleService
from app.application.use_cases.run_scheduled_reports import ReportScheduleRunnerService
from app.domain.exceptions import (
    DomainError,
    ReportScheduleNotFound,
    ReportScheduleRecipientNotFound,
    ReportTemplateNotFound,
)
from app.infrastructure.db.repository_impl import (
    SqlAlchemyGeneratedReportLogRepository,
    SqlAlchemyReportFilterConfigRepository,
    SqlAlchemyReportScheduleRecipientRepository,
    SqlAlchemyReportScheduleRepository,
    SqlAlchemyReportScheduleRunLogRepository,
    SqlAlchemyReportTemplateRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.report_email_sender import get_report_email_sender
from app.infrastructure.semantic_layer_report_client import (
    get_semantic_layer_report_query_client,
)
from app.interfaces.api.schemas import (
    ErrorResponse,
    ReportScheduleCreate,
    ReportScheduleRecipientCreate,
    ReportScheduleRecipientResponse,
    ReportScheduleResponse,
    ReportScheduleRunLogResponse,
    ReportScheduleUpdate,
)

router = APIRouter(
    prefix="/report-templates/{template_id}/schedules",
    tags=["UC-051 Cấu hình báo cáo theo lịch"],
)


def get_report_schedule_service(db: Session = Depends(get_db)) -> ReportScheduleService:
    return ReportScheduleService(
        schedule_repo=SqlAlchemyReportScheduleRepository(db),
        recipient_repo=SqlAlchemyReportScheduleRecipientRepository(db),
        run_log_repo=SqlAlchemyReportScheduleRunLogRepository(db),
        template_repo=SqlAlchemyReportTemplateRepository(db),
    )


def get_report_schedule_runner_service(
    db: Session = Depends(get_db),
) -> ReportScheduleRunnerService:
    return ReportScheduleRunnerService(
        schedule_repo=SqlAlchemyReportScheduleRepository(db),
        recipient_repo=SqlAlchemyReportScheduleRecipientRepository(db),
        run_log_repo=SqlAlchemyReportScheduleRunLogRepository(db),
        report_generation_service=ReportGenerationService(
            template_repo=SqlAlchemyReportTemplateRepository(db),
            filter_config_repo=SqlAlchemyReportFilterConfigRepository(db),
            query_client=get_semantic_layer_report_query_client(),
            log_repo=SqlAlchemyGeneratedReportLogRepository(db),
        ),
        email_sender=get_report_email_sender(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(
        exc, (ReportScheduleNotFound, ReportTemplateNotFound, ReportScheduleRecipientNotFound)
    ):
        status_code = 404
    elif exc.code in ("REPORT_TEMPLATE_INACTIVE", "REPORT_SCHEDULE_RECIPIENT_EXISTS"):
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "",
    response_model=ReportScheduleResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_schedule(
    template_id: int,
    payload: ReportScheduleCreate,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    """Bước 1 — "Cấu hình lịch (hàng ngày/hàng tuần/hàng tháng) -> hệ
    thống lưu lịch"."""
    try:
        return service.configure(template_id=template_id, **payload.model_dump())
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[ReportScheduleResponse])
def list_schedules(
    template_id: int,
    user_id: int = Query(..., gt=0),
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    """Danh sách lịch báo cáo đã cấu hình của người dùng cho mẫu này."""
    return service.list_for_user(user_id, template_id=template_id)


@router.get(
    "/{schedule_id}",
    response_model=ReportScheduleResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_schedule(
    template_id: int,
    schedule_id: int,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        return service.get(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{schedule_id}",
    response_model=ReportScheduleResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_schedule(
    template_id: int,
    schedule_id: int,
    payload: ReportScheduleUpdate,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    """Sửa cấu hình lịch đã có (tần suất/giờ chạy/định dạng/bộ lọc)."""
    try:
        return service.update_config(schedule_id=schedule_id, **payload.model_dump())
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{schedule_id}/enable",
    response_model=ReportScheduleResponse,
    responses={404: {"model": ErrorResponse}},
)
def enable_schedule(
    template_id: int,
    schedule_id: int,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        return service.enable(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{schedule_id}/disable",
    response_model=ReportScheduleResponse,
    responses={404: {"model": ErrorResponse}},
)
def disable_schedule(
    template_id: int,
    schedule_id: int,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        return service.disable(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Cấu hình người nhận (email) -> hệ thống lưu ----------


@router.post(
    "/{schedule_id}/recipients",
    response_model=ReportScheduleRecipientResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def add_recipient(
    template_id: int,
    schedule_id: int,
    payload: ReportScheduleRecipientCreate,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        return service.add_recipient(schedule_id, payload.email)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{schedule_id}/recipients",
    response_model=List[ReportScheduleRecipientResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_recipients(
    template_id: int,
    schedule_id: int,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        return service.list_recipients(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete(
    "/{schedule_id}/recipients/{email}",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
)
def remove_recipient(
    template_id: int,
    schedule_id: int,
    email: str,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    try:
        service.remove_recipient(schedule_id, email)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return None


# ---------- Bước 3: Hệ thống tự động sinh + gửi email báo cáo theo lịch ----------


@router.post(
    "/{schedule_id}/run-now",
    response_model=ReportScheduleRunLogResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def run_schedule_now(
    template_id: int,
    schedule_id: int,
    runner: ReportScheduleRunnerService = Depends(get_report_schedule_runner_service),
):
    """Chạy thử ngay 1 lịch (bỏ qua kiểm tra tới hạn) — mô phỏng đúng
    hành vi "tác vụ định kỳ (cron)" thật sự sẽ làm khi tới hạn, dùng để
    kiểm tra cấu hình lịch/người nhận trước khi chờ tới hạn thật."""
    try:
        return runner.run_now(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{schedule_id}/logs",
    response_model=List[ReportScheduleRunLogResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_run_logs(
    template_id: int,
    schedule_id: int,
    service: ReportScheduleService = Depends(get_report_schedule_service),
):
    """Lịch sử các lần tác vụ định kỳ (cron) đã chạy cho lịch này."""
    try:
        return service.list_run_logs(schedule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)