from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.approve_catalog_change import CatalogChangeApprovalService
from app.application.use_cases.manage_catalog_entry import CatalogEntryService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCatalogChangeAuditLogRepository,
    SqlAlchemyCatalogChangeRequestRepository,
    SqlAlchemyCatalogEntryRepository,
    SqlAlchemyCatalogEntryVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CatalogChangeApprovalDecision,
    CatalogChangeApprovalResultResponse,
    CatalogChangeAuditLogResponse,
    CatalogChangeDiffFieldResponse,
    CatalogChangeDiffResponse,
    CatalogChangeRejectionResultResponse,
    CatalogChangeRequestResponse,
    CatalogEntryResponse,
    ErrorResponse,
)

router = APIRouter(
    prefix="/catalog-change-approvals",
    tags=["UC-037 Phê duyệt thay đổi danh mục nhạy cảm"],
)


def get_service(db: Session = Depends(get_db)) -> CatalogChangeApprovalService:
    catalog_entry_service = CatalogEntryService(
        entry_repo=SqlAlchemyCatalogEntryRepository(db),
        version_repo=SqlAlchemyCatalogEntryVersionRepository(db),
        change_request_repo=SqlAlchemyCatalogChangeRequestRepository(db),
    )
    return CatalogChangeApprovalService(
        catalog_entry_service=catalog_entry_service,
        audit_log_repo=SqlAlchemyCatalogChangeAuditLogRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem các yêu cầu chờ duyệt ----------


@router.get("/pending", response_model=List[CatalogChangeRequestResponse])
def list_pending_change_requests(
    catalog_type: Optional[str] = Query(
        None, description="ITEM (mặt hàng) / DOCUMENT_TYPE (loại văn bản) / FUNDING_SOURCE (nguồn vốn)"
    ),
    service: CatalogChangeApprovalService = Depends(get_service),
):
    """Bước 1 'Xem các yêu cầu chờ duyệt' -- hệ thống hiển thị danh sách

    yêu cầu thay đổi danh mục nhạy cảm đang chờ duyệt (UC-036 bước 3)."""
    requests = service.list_pending_requests(catalog_type=catalog_type)
    return [CatalogChangeRequestResponse.from_entity(r) for r in requests]


# ---------- Bước 2: Hệ thống hiển thị diff ----------


@router.get(
    "/{request_id}/diff",
    response_model=CatalogChangeDiffResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_change_request_diff(
    request_id: int, service: CatalogChangeApprovalService = Depends(get_service)
):
    """Bước 2 'Hệ thống hiển thị diff' -- so sánh giá trị hiện tại của

    mục danh mục với từng trường được đề nghị thay đổi."""
    try:
        diff_info = service.get_diff(request_id)
        return CatalogChangeDiffResponse(
            request=CatalogChangeRequestResponse.from_entity(diff_info["request"]),
            entry=CatalogEntryResponse.from_entity(diff_info["entry"]),
            changes=[CatalogChangeDiffFieldResponse.from_dict(c) for c in diff_info["changes"]],
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3 + 4 + 5: Phê duyệt / từ chối -- áp dụng -- ghi nhật ký ----------


@router.post(
    "/{request_id}/approve",
    response_model=CatalogChangeApprovalResultResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def approve_change_request(
    request_id: int,
    payload: CatalogChangeApprovalDecision,
    service: CatalogChangeApprovalService = Depends(get_service),
):
    """Bước 3 'Phê duyệt' -- bước 4 'Hệ thống cập nhật và áp dụng thay

    đổi' -- bước 5 'Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký'
    (`reason` bắt buộc, trả 422 nếu để trống)."""
    try:
        result = service.approve(request_id, decided_by=payload.decided_by, reason=payload.reason)
        return CatalogChangeApprovalResultResponse(
            entry=CatalogEntryResponse.from_entity(result["entry"]),
            audit_log=CatalogChangeAuditLogResponse.from_entity(result["audit_log"]),
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{request_id}/reject",
    response_model=CatalogChangeRejectionResultResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_change_request(
    request_id: int,
    payload: CatalogChangeApprovalDecision,
    service: CatalogChangeApprovalService = Depends(get_service),
):
    """Bước 3 'Từ chối' -- KHÔNG áp dụng thay đổi -- bước 5 'Ghi lý do

    phê duyệt -- Hệ thống lưu vào nhật ký' (`reason` bắt buộc)."""
    try:
        result = service.reject(request_id, decided_by=payload.decided_by, reason=payload.reason)
        return CatalogChangeRejectionResultResponse(
            request=CatalogChangeRequestResponse.from_entity(result["request"]),
            audit_log=CatalogChangeAuditLogResponse.from_entity(result["audit_log"]),
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 5: tra cứu nhật ký ----------


@router.get("/audit-logs", response_model=List[CatalogChangeAuditLogResponse])
def list_change_approval_audit_logs(
    request_id: Optional[int] = Query(None),
    entry_id: Optional[int] = Query(None),
    catalog_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None, description="APPROVED/REJECTED"),
    service: CatalogChangeApprovalService = Depends(get_service),
):
    """Bước 5 'Hệ thống lưu vào nhật ký' -- tra cứu lại nhật ký các

    quyết định phê duyệt/từ chối đã ghi."""
    logs = service.list_audit_logs(
        request_id=request_id, entry_id=entry_id, catalog_type=catalog_type, action=action
    )
    return [CatalogChangeAuditLogResponse.from_entity(log) for log in logs]