from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_budget_item_catalog import BudgetItemCatalogService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyBudgetItemCatalogRepository,
    SqlAlchemyBudgetItemCatalogVersionRepository,
    SqlAlchemyBudgetItemChangeRequestRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    BudgetItemCatalogCreate,
    BudgetItemCatalogResponse,
    BudgetItemCatalogUpdate,
    BudgetItemCatalogVersionResponse,
    BudgetItemChangeRequestCreate,
    BudgetItemChangeRequestResponse,
    BudgetItemChangeReviewRequest,
    BudgetItemTreeNodeResponse,
    ErrorResponse,
)

router = APIRouter(
    prefix="/budget-item-catalog", tags=["UC-034 Quản lý danh mục khoản mục NSNN"]
)


def get_service(db: Session = Depends(get_db)) -> BudgetItemCatalogService:
    return BudgetItemCatalogService(
        item_repo=SqlAlchemyBudgetItemCatalogRepository(db),
        version_repo=SqlAlchemyBudgetItemCatalogVersionRepository(db),
        change_request_repo=SqlAlchemyBudgetItemChangeRequestRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "EXISTS" in exc.code:
        status_code = 409
    elif "REQUIRES_APPROVAL" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem cây khoản mục NSNN ----------


@router.get("/tree", response_model=List[BudgetItemTreeNodeResponse])
def get_budget_item_tree(
    budget_year: int = Query(..., description="Năm ngân sách cần xem"),
    include_closed: bool = Query(True, description="True (mặc định) để gồm cả khoản mục đã đóng"),
    service: BudgetItemCatalogService = Depends(get_service),
):
    """Bước 1 'Xem cây khoản mục NSNN (Chương/Loại/Khoản/Mục/Tiểu mục)' --

    hệ thống hiển thị."""
    tree = service.get_tree(budget_year=budget_year, include_closed=include_closed)
    return [BudgetItemTreeNodeResponse.from_node(n) for n in tree]


@router.get("", response_model=List[BudgetItemCatalogResponse])
def list_budget_items(
    budget_year: Optional[int] = Query(None),
    parent_id: Optional[int] = Query(None, description="Lọc theo khoản mục cha (bỏ trống = tất cả)"),
    only_root: bool = Query(False, description="True để chỉ lấy khoản mục gốc (Chương)"),
    level: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="ACTIVE hoặc CLOSED"),
    service: BudgetItemCatalogService = Depends(get_service),
):
    if only_root:
        resolved_parent_id: Optional[int] = None
    elif parent_id is not None:
        resolved_parent_id = parent_id
    else:
        resolved_parent_id = "__unset__"
    items = service.list_items(
        budget_year=budget_year, parent_id=resolved_parent_id, level=level, status=status
    )
    return [BudgetItemCatalogResponse.from_entity(i) for i in items]


@router.get(
    "/{item_id}",
    response_model=BudgetItemCatalogResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_budget_item(item_id: int, service: BudgetItemCatalogService = Depends(get_service)):
    try:
        return BudgetItemCatalogResponse.from_entity(service.get(item_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{item_id}/versions",
    response_model=List[BudgetItemCatalogVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_budget_item_versions(
    item_id: int, service: BudgetItemCatalogService = Depends(get_service)
):
    try:
        versions = service.list_versions(item_id)
        return [BudgetItemCatalogVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Thêm / Sửa entry (quản lý phiên bản theo năm) ----------


@router.post(
    "",
    response_model=BudgetItemCatalogResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_budget_item(
    payload: BudgetItemCatalogCreate, service: BudgetItemCatalogService = Depends(get_service)
):
    """Bước 2 'Thêm entry' -- hệ thống quản lý phiên bản theo năm ngân sách."""
    try:
        item = service.create_item(
            code=payload.code,
            name=payload.name,
            level=payload.level,
            budget_year=payload.budget_year,
            parent_id=payload.parent_id,
            is_sensitive=payload.is_sensitive,
            effective_from=payload.effective_from,
            note=payload.note,
        )
        return BudgetItemCatalogResponse.from_entity(item)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{item_id}",
    response_model=BudgetItemCatalogResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def update_budget_item(
    item_id: int,
    payload: BudgetItemCatalogUpdate,
    service: BudgetItemCatalogService = Depends(get_service),
):
    """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản theo năm ngân

    sách (tăng version + ghi lịch sử). Trả 409
    `BUDGET_ITEM_SENSITIVE_REQUIRES_APPROVAL` nếu khoản mục là khoản mục
    nhạy cảm -- dùng bước 3 (`/change-requests`) thay thế."""
    try:
        item = service.update_item(
            item_id, name=payload.name, status=payload.status, note=payload.note
        )
        return BudgetItemCatalogResponse.from_entity(item)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Đề nghị thay đổi khoản mục nhạy cảm ----------


@router.post(
    "/{item_id}/change-requests",
    response_model=BudgetItemChangeRequestResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def propose_budget_item_change(
    item_id: int,
    payload: BudgetItemChangeRequestCreate,
    service: BudgetItemCatalogService = Depends(get_service),
):
    """Bước 3 'Đề nghị thay đổi khoản mục nhạy cảm' -- hệ thống lưu yêu

    cầu chờ duyệt (KHÔNG áp dụng thay đổi ngay)."""
    try:
        request = service.propose_change(
            item_id=item_id,
            requested_by=payload.requested_by,
            reason=payload.reason,
            proposed_name=payload.proposed_name,
            proposed_status=payload.proposed_status,
            proposed_is_sensitive=payload.proposed_is_sensitive,
        )
        return BudgetItemChangeRequestResponse.from_entity(request)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/change-requests/list", response_model=List[BudgetItemChangeRequestResponse])
def list_budget_item_change_requests(
    item_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="PENDING/APPROVED/REJECTED"),
    service: BudgetItemCatalogService = Depends(get_service),
):
    requests = service.list_change_requests(item_id=item_id, status=status)
    return [BudgetItemChangeRequestResponse.from_entity(r) for r in requests]


@router.get(
    "/change-requests/{request_id}",
    response_model=BudgetItemChangeRequestResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_budget_item_change_request(
    request_id: int, service: BudgetItemCatalogService = Depends(get_service)
):
    try:
        return BudgetItemChangeRequestResponse.from_entity(
            service.get_change_request(request_id)
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/change-requests/{request_id}/approve",
    response_model=BudgetItemCatalogResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def approve_budget_item_change(
    request_id: int,
    payload: BudgetItemChangeReviewRequest,
    service: BudgetItemCatalogService = Depends(get_service),
):
    """Duyệt yêu cầu -- áp dụng thay đổi vào khoản mục (tăng version +

    ghi lịch sử)."""
    try:
        item = service.approve_change(
            request_id, reviewed_by=payload.reviewed_by, review_note=payload.review_note
        )
        return BudgetItemCatalogResponse.from_entity(item)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/change-requests/{request_id}/reject",
    response_model=BudgetItemChangeRequestResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_budget_item_change(
    request_id: int,
    payload: BudgetItemChangeReviewRequest,
    service: BudgetItemCatalogService = Depends(get_service),
):
    try:
        request = service.reject_change(
            request_id, reviewed_by=payload.reviewed_by, review_note=payload.review_note
        )
        return BudgetItemChangeRequestResponse.from_entity(request)
    except DomainError as exc:
        raise _domain_error_to_http(exc)