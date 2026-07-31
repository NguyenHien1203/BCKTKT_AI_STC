from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_reconciliation_ticket import ReconciliationTicketService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyIntakeReconciliationRepository,
    SqlAlchemyReconciliationTicketRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    ReconciliationTicketCloseRequest,
    ReconciliationTicketOpenRequest,
    ReconciliationTicketProgressRequest,
    ReconciliationTicketResponse,
)

router = APIRouter(
    prefix="/reconciliation-tickets",
    tags=["UC-028 Xử lý ticket đối soát với chủ quản nguồn"],
)


def get_service(db: Session = Depends(get_db)) -> ReconciliationTicketService:
    """Tái sử dụng `IntakeReconciliationRepository` (UC-027) chỉ để xác
    nhận phiên đối soát tồn tại khi mở ticket."""
    return ReconciliationTicketService(
        ticket_repo=SqlAlchemyReconciliationTicketRepository(db),
        reconciliation_repo=SqlAlchemyIntakeReconciliationRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu + thông báo ----------


@router.post(
    "",
    response_model=ReconciliationTicketResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def open_reconciliation_ticket(
    payload: ReconciliationTicketOpenRequest,
    service: ReconciliationTicketService = Depends(get_service),
):
    """Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu ticket + thông
    báo (mô phỏng bằng cờ `notified`)."""
    try:
        return service.open_ticket(
            reconciliation_id=payload.reconciliation_id,
            source_owner=payload.source_owner,
            title=payload.title,
            description=payload.description,
            opened_by=payload.opened_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xem lại ticket ----------


@router.get("", response_model=List[ReconciliationTicketResponse])
def list_reconciliation_tickets(
    reconciliation_id: Optional[int] = None,
    status: Optional[str] = None,
    service: ReconciliationTicketService = Depends(get_service),
):
    """Xem danh sách ticket (lọc theo phiên đối soát/trạng thái)."""
    return service.list_tickets(reconciliation_id=reconciliation_id, status=status)


@router.get(
    "/{ticket_id}",
    response_model=ReconciliationTicketResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_reconciliation_ticket(
    ticket_id: int, service: ReconciliationTicketService = Depends(get_service)
):
    """Xem chi tiết 1 ticket: trạng thái + lịch sử xử lý."""
    try:
        return service.get(ticket_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử ----------


@router.post(
    "/{ticket_id}/progress",
    response_model=ReconciliationTicketResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def add_reconciliation_ticket_progress(
    ticket_id: int,
    payload: ReconciliationTicketProgressRequest,
    service: ReconciliationTicketService = Depends(get_service),
):
    """Cập nhật tiến độ xử lý ticket (kèm tuỳ chọn chuyển trạng thái
    OPEN/IN_PROGRESS/RESOLVED) -> hệ thống lưu ngay vào lịch sử."""
    try:
        return service.add_progress(
            ticket_id=ticket_id,
            note=payload.note,
            updated_by=payload.updated_by,
            status=payload.status,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký ----------


@router.post(
    "/{ticket_id}/close",
    response_model=ReconciliationTicketResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def close_reconciliation_ticket(
    ticket_id: int,
    payload: ReconciliationTicketCloseRequest,
    service: ReconciliationTicketService = Depends(get_service),
):
    """Đóng ticket khi đã resolved -> hệ thống cập nhật trạng thái
    RESOLVED -> CLOSED + ghi nhật ký (lưu vào lịch sử)."""
    try:
        return service.close(
            ticket_id=ticket_id,
            closed_by=payload.closed_by,
            close_note=payload.close_note,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)