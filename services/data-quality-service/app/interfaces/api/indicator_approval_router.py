from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.approve_semantic_indicator import IndicatorApprovalService
from app.application.use_cases.manage_semantic_indicator import SemanticIndicatorService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyIndicatorApprovalDecisionRepository,
    SqlAlchemyIndicatorAuditLogRepository,
    SqlAlchemyIndicatorTestRunRepository,
    SqlAlchemySemanticIndicatorRepository,
    SqlAlchemySemanticIndicatorVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    IndicatorApprovalDecisionRequest,
    IndicatorApprovalDecisionResponse,
    IndicatorApprovalResultResponse,
    IndicatorComparisonResponse,
    SemanticIndicatorResponse,
    SubmitIndicatorApprovalRequest,
)

router = APIRouter(prefix="/indicator-approvals", tags=["UC-044 Phê duyệt chỉ tiêu"])


def get_service(db: Session = Depends(get_db)) -> IndicatorApprovalService:
    indicator_service = SemanticIndicatorService(
        indicator_repo=SqlAlchemySemanticIndicatorRepository(db),
        version_repo=SqlAlchemySemanticIndicatorVersionRepository(db),
        test_run_repo=SqlAlchemyIndicatorTestRunRepository(db),
        audit_log_repo=SqlAlchemyIndicatorAuditLogRepository(db),
    )
    return IndicatorApprovalService(
        indicator_service=indicator_service,
        decision_repo=SqlAlchemyIndicatorApprovalDecisionRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "EXISTS" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Tiền đề: gửi chỉ tiêu chờ phê duyệt ----------


@router.post(
    "/{indicator_id}/submit",
    response_model=SemanticIndicatorResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def submit_indicator_for_approval(
    indicator_id: int,
    payload: SubmitIndicatorApprovalRequest,
    service: IndicatorApprovalService = Depends(get_service),
):
    """Quản trị Dữ liệu gửi 1 chỉ tiêu đang DRAFT để chờ Chủ quản

    Nghiệp vụ phê duyệt (status -> PENDING_APPROVAL)."""
    try:
        indicator = service.submit_for_approval(
            indicator_id, submitted_by=payload.submitted_by, note=payload.note
        )
        return SemanticIndicatorResponse.from_entity(indicator)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 1: Xem chỉ tiêu chờ phê duyệt ----------


@router.get("/pending", response_model=List[SemanticIndicatorResponse])
def list_pending_indicator_approvals(
    domain: Optional[str] = Query(None, description="Lọc theo lĩnh vực"),
    service: IndicatorApprovalService = Depends(get_service),
):
    """Bước 1 'Xem chỉ tiêu chờ phê duyệt'. Hệ thống hiển thị."""
    items = service.list_pending(domain=domain)
    return [SemanticIndicatorResponse.from_entity(i) for i in items]


# ---------- Bước 2: Xem kết quả kiểm thử + so sánh với số liệu hiện tại ----------


@router.get(
    "/{indicator_id}/comparison",
    response_model=IndicatorComparisonResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_indicator_comparison(
    indicator_id: int, service: IndicatorApprovalService = Depends(get_service)
):
    """Bước 2 'Xem kết quả kiểm thử + so sánh với số liệu hiện tại'.

    Hệ thống hiển thị."""
    try:
        return IndicatorComparisonResponse.from_dict(service.get_comparison(indicator_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Phê duyệt / từ chối chỉ tiêu ----------


@router.post(
    "/{indicator_id}/approve",
    response_model=IndicatorApprovalResultResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def approve_indicator(
    indicator_id: int,
    payload: IndicatorApprovalDecisionRequest,
    service: IndicatorApprovalService = Depends(get_service),
):
    """Bước 3 'Phê duyệt chỉ tiêu'. Hệ thống CÔNG BỐ (status=ACTIVE)."""
    try:
        result = service.approve(
            indicator_id, decided_by=payload.decided_by, reason=payload.reason, note=payload.note
        )
        return IndicatorApprovalResultResponse.from_dict(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{indicator_id}/reject",
    response_model=IndicatorApprovalResultResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_indicator(
    indicator_id: int,
    payload: IndicatorApprovalDecisionRequest,
    service: IndicatorApprovalService = Depends(get_service),
):
    """Bước 3 'Từ chối chỉ tiêu'. Hệ thống TRẢ VỀ cho Quản trị Dữ liệu

    (status=DRAFT)."""
    try:
        result = service.reject(
            indicator_id, decided_by=payload.decided_by, reason=payload.reason, note=payload.note
        )
        return IndicatorApprovalResultResponse.from_dict(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Tra cứu: nhật ký quyết định ----------


@router.get(
    "/{indicator_id}/decisions",
    response_model=List[IndicatorApprovalDecisionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_indicator_approval_decisions(
    indicator_id: int, service: IndicatorApprovalService = Depends(get_service)
):
    try:
        decisions = service.list_decisions(indicator_id)
        return [IndicatorApprovalDecisionResponse.from_entity(d) for d in decisions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)