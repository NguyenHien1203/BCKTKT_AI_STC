from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_intake_reconciliation import IntakeReconciliationService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyIntakeReconciliationRepository,
    SqlAlchemyTabmisIntakeSessionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    IntakeReconciliationCloseRequest,
    IntakeReconciliationFindingRequest,
    IntakeReconciliationOpenRequest,
    IntakeReconciliationResponse,
)

router = APIRouter(
    prefix="/intake-reconciliations", tags=["UC-027 Đối soát phiên intake"]
)


def get_service(db: Session = Depends(get_db)) -> IntakeReconciliationService:
    """Tái sử dụng `TabmisIntakeSessionRepository` (UC-022/023) để lấy
    phiên tiếp nhận + tổng kiểm soát (`control_totals`) cần đối soát."""
    return IntakeReconciliationService(
        reconciliation_repo=SqlAlchemyIntakeReconciliationRepository(db),
        session_repo=SqlAlchemyTabmisIntakeSessionRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-2: Chọn phiên cần đối soát -> hệ thống hiển thị tổng kiểm soát ----------


@router.post(
    "",
    response_model=IntakeReconciliationResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def open_intake_reconciliation(
    payload: IntakeReconciliationOpenRequest,
    service: IntakeReconciliationService = Depends(get_service),
):
    """Chọn phiên cần đối soát: hệ thống mở 1 phiên đối soát mới (hoặc trả
    về phiên đối soát đang mở nếu đã có) gắn với phiên tiếp nhận
    `session_id`, kèm theo tổng kiểm soát (`control_totals`) để hiển thị."""
    try:
        return service.open_or_get(
            session_id=payload.session_id, reconciled_by=payload.reconciled_by
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xem lại phiên đối soát ----------


@router.get("", response_model=List[IntakeReconciliationResponse])
def list_intake_reconciliations(
    session_id: Optional[int] = None,
    status: Optional[str] = None,
    service: IntakeReconciliationService = Depends(get_service),
):
    """Xem danh sách phiên đối soát (lọc theo phiên tiếp nhận/trạng thái)."""
    return service.list_reconciliations(session_id=session_id, status=status)


@router.get(
    "/{reconciliation_id}",
    response_model=IntakeReconciliationResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_intake_reconciliation(
    reconciliation_id: int, service: IntakeReconciliationService = Depends(get_service)
):
    """Xem chi tiết 1 phiên đối soát: tổng kiểm soát + danh sách phát hiện."""
    try:
        return service.get(reconciliation_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu ----------


@router.post(
    "/{reconciliation_id}/findings",
    response_model=IntakeReconciliationResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def mark_finding(
    reconciliation_id: int,
    payload: IntakeReconciliationFindingRequest,
    service: IntakeReconciliationService = Depends(get_service),
):
    """Đánh dấu phát hiện thiếu (MISSING) hoặc sai (INCORRECT) so với tổng
    kiểm soát -> hệ thống lưu ngay vào phiên đối soát."""
    try:
        return service.mark_finding(
            reconciliation_id=reconciliation_id,
            finding_type=payload.finding_type,
            field_name=payload.field_name,
            description=payload.description,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xử lý xong 1 phát hiện (điều kiện để đóng phiên "đạt yêu cầu") ----------


@router.post(
    "/{reconciliation_id}/findings/{finding_index}/resolve",
    response_model=IntakeReconciliationResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def resolve_finding(
    reconciliation_id: int,
    finding_index: int,
    service: IntakeReconciliationService = Depends(get_service),
):
    """Đánh dấu 1 phát hiện đã được xử lý xong — điều kiện để đóng phiên
    đối soát "đạt yêu cầu" ở bước tiếp theo."""
    try:
        return service.resolve_finding(reconciliation_id, finding_index)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> hệ thống cập nhật trạng thái ----------


@router.post(
    "/{reconciliation_id}/close",
    response_model=IntakeReconciliationResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def close_intake_reconciliation(
    reconciliation_id: int,
    payload: IntakeReconciliationCloseRequest,
    service: IntakeReconciliationService = Depends(get_service),
):
    """Đóng phiên đối soát đạt yêu cầu: chỉ cho phép khi không còn phát
    hiện nào chưa xử lý xong -> hệ thống cập nhật trạng thái OPEN -> CLOSED."""
    try:
        return service.close(
            reconciliation_id=reconciliation_id,
            closed_by=payload.closed_by,
            close_note=payload.close_note,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)