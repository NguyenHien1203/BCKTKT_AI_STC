from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_scheduled_task import ScheduledTaskService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDatasetRepository,
    SqlAlchemyScheduledTaskRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    ScheduledTaskConfigUpdate,
    ScheduledTaskCreate,
    ScheduledTaskResponse,
    ScheduledTaskRunStatusUpdate,
)

router = APIRouter(prefix="/scheduled-tasks", tags=["UC-019 Cấu hình tác vụ điều phối"])


def get_service(db: Session = Depends(get_db)) -> ScheduledTaskService:
    return ScheduledTaskService(
        scheduled_task_repo=SqlAlchemyScheduledTaskRepository(db),
        dataset_repo=SqlAlchemyDatasetRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Cấu hình tác vụ điều phối ----------


@router.post(
    "",
    response_model=ScheduledTaskResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def configure_scheduled_task(
    payload: ScheduledTaskCreate, service: ScheduledTaskService = Depends(get_service)
):
    """Cấu hình tác vụ điều phối (lịch cron, đầy đủ/tăng dần, chính sách
    thử lại): hệ thống lưu."""
    try:
        return service.configure(
            dataset_id=payload.dataset_id,
            code=payload.code,
            name=payload.name,
            sync_mode=payload.sync_mode,
            cron_expression=payload.cron_expression,
            retry_max_attempts=payload.retry_max_attempts,
            retry_delay_seconds=payload.retry_delay_seconds,
            retry_backoff=payload.retry_backoff,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[ScheduledTaskResponse])
def list_scheduled_tasks(
    dataset_id: Optional[int] = Query(None),
    only_enabled: bool = Query(False),
    service: ScheduledTaskService = Depends(get_service),
):
    return service.list_tasks(dataset_id=dataset_id, only_enabled=only_enabled)


@router.get(
    "/{task_id}",
    response_model=ScheduledTaskResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_scheduled_task(task_id: int, service: ScheduledTaskService = Depends(get_service)):
    try:
        return service.get(task_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{task_id}",
    response_model=ScheduledTaskResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_scheduled_task_config(
    task_id: int,
    payload: ScheduledTaskConfigUpdate,
    service: ScheduledTaskService = Depends(get_service),
):
    """Sửa cấu hình tác vụ điều phối: hệ thống lưu."""
    try:
        return service.update_config(
            task_id,
            sync_mode=payload.sync_mode,
            cron_expression=payload.cron_expression,
            retry_max_attempts=payload.retry_max_attempts,
            retry_delay_seconds=payload.retry_delay_seconds,
            retry_backoff=payload.retry_backoff,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bật / tắt tác vụ điều phối ----------


@router.post(
    "/{task_id}/enable",
    response_model=ScheduledTaskResponse,
    responses={404: {"model": ErrorResponse}},
)
def enable_scheduled_task(task_id: int, service: ScheduledTaskService = Depends(get_service)):
    """Bật tác vụ điều phối: hệ thống cập nhật trạng thái tác vụ điều
    phối."""
    try:
        return service.enable(task_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{task_id}/disable",
    response_model=ScheduledTaskResponse,
    responses={404: {"model": ErrorResponse}},
)
def disable_scheduled_task(task_id: int, service: ScheduledTaskService = Depends(get_service)):
    """Tắt tác vụ điều phối: hệ thống cập nhật trạng thái tác vụ điều
    phối."""
    try:
        return service.disable(task_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Hệ thống cập nhật trạng thái thực thi (Bộ điều phối) ----------


@router.post(
    "/{task_id}/status",
    response_model=ScheduledTaskResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def record_run_status(
    task_id: int,
    payload: ScheduledTaskRunStatusUpdate,
    service: ScheduledTaskService = Depends(get_service),
):
    """Hệ thống (Bộ điều phối, xem UC-025) cập nhật trạng thái tác vụ
    điều phối sau khi thực thi 1 phiên."""
    try:
        return service.record_run_status(
            task_id, status=payload.status, message=payload.message, run_at=payload.run_at
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)