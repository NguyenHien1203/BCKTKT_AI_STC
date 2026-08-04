from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_catalog_entry import CatalogEntryService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCatalogChangeRequestRepository,
    SqlAlchemyCatalogEntryRepository,
    SqlAlchemyCatalogEntryVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CatalogChangeRequestCreate,
    CatalogChangeRequestResponse,
    CatalogChangeReviewRequest,
    CatalogEntryCreate,
    CatalogEntryResponse,
    CatalogEntryUpdate,
    CatalogEntryVersionResponse,
    ErrorResponse,
)

router = APIRouter(
    prefix="/catalog-entries",
    tags=["UC-036 Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn"],
)


def get_service(db: Session = Depends(get_db)) -> CatalogEntryService:
    return CatalogEntryService(
        entry_repo=SqlAlchemyCatalogEntryRepository(db),
        version_repo=SqlAlchemyCatalogEntryVersionRepository(db),
        change_request_repo=SqlAlchemyCatalogChangeRequestRepository(db),
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


# ---------- Bước 1: Xem từng danh mục (mặt hàng / loại văn bản / nguồn vốn) ----------


@router.get("", response_model=List[CatalogEntryResponse])
def list_catalog_entries(
    catalog_type: Optional[str] = Query(
        None, description="ITEM (mặt hàng) / DOCUMENT_TYPE (loại văn bản) / FUNDING_SOURCE (nguồn vốn)"
    ),
    status: Optional[str] = Query(None, description="ACTIVE hoặc CLOSED"),
    service: CatalogEntryService = Depends(get_service),
):
    """Bước 1 'Xem từng danh mục (mặt hàng / loại văn bản / nguồn vốn)'

    -- hệ thống hiển thị. Lọc theo `catalog_type` để xem riêng 1 danh
    mục, bỏ trống để xem toàn bộ."""
    entries = service.list_entries(catalog_type=catalog_type, status=status)
    return [CatalogEntryResponse.from_entity(e) for e in entries]


@router.get(
    "/{entry_id}",
    response_model=CatalogEntryResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_catalog_entry(entry_id: int, service: CatalogEntryService = Depends(get_service)):
    try:
        return CatalogEntryResponse.from_entity(service.get(entry_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{entry_id}/versions",
    response_model=List[CatalogEntryVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_catalog_entry_versions(
    entry_id: int, service: CatalogEntryService = Depends(get_service)
):
    try:
        versions = service.list_versions(entry_id)
        return [CatalogEntryVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Thêm / Sửa entry (hệ thống quản lý phiên bản) ----------


@router.post(
    "",
    response_model=CatalogEntryResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_catalog_entry(
    payload: CatalogEntryCreate, service: CatalogEntryService = Depends(get_service)
):
    """Bước 2 'Thêm entry' -- hệ thống quản lý phiên bản."""
    try:
        entry = service.create_entry(
            catalog_type=payload.catalog_type,
            code=payload.code,
            name=payload.name,
            unit=payload.unit,
            description=payload.description,
            is_sensitive=payload.is_sensitive,
            effective_from=payload.effective_from,
            note=payload.note,
        )
        return CatalogEntryResponse.from_entity(entry)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{entry_id}",
    response_model=CatalogEntryResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def update_catalog_entry(
    entry_id: int,
    payload: CatalogEntryUpdate,
    service: CatalogEntryService = Depends(get_service),
):
    """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản (tăng version +

    ghi lịch sử). Trả 409 `CATALOG_ENTRY_SENSITIVE_REQUIRES_APPROVAL`
    nếu mục là mục nhạy cảm -- dùng bước 3 (`/change-requests`) thay
    thế."""
    try:
        entry = service.update_entry(
            entry_id,
            name=payload.name,
            unit=payload.unit,
            description=payload.description,
            status=payload.status,
            note=payload.note,
        )
        return CatalogEntryResponse.from_entity(entry)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Đề nghị thay đổi danh mục nhạy cảm ----------


@router.post(
    "/{entry_id}/change-requests",
    response_model=CatalogChangeRequestResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def propose_catalog_entry_change(
    entry_id: int,
    payload: CatalogChangeRequestCreate,
    service: CatalogEntryService = Depends(get_service),
):
    """Bước 3 'Đề nghị thay đổi danh mục nhạy cảm' -- hệ thống lưu yêu

    cầu chờ duyệt (KHÔNG áp dụng thay đổi ngay). Người có thẩm quyền
    duyệt/từ chối ở UC-037."""
    try:
        request = service.propose_change(
            entry_id=entry_id,
            requested_by=payload.requested_by,
            reason=payload.reason,
            proposed_name=payload.proposed_name,
            proposed_unit=payload.proposed_unit,
            proposed_description=payload.proposed_description,
            proposed_status=payload.proposed_status,
            proposed_is_sensitive=payload.proposed_is_sensitive,
        )
        return CatalogChangeRequestResponse.from_entity(request)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/change-requests/list", response_model=List[CatalogChangeRequestResponse])
def list_catalog_entry_change_requests(
    entry_id: Optional[int] = Query(None),
    catalog_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="PENDING/APPROVED/REJECTED"),
    service: CatalogEntryService = Depends(get_service),
):
    requests = service.list_change_requests(
        entry_id=entry_id, catalog_type=catalog_type, status=status
    )
    return [CatalogChangeRequestResponse.from_entity(r) for r in requests]


@router.get(
    "/change-requests/{request_id}",
    response_model=CatalogChangeRequestResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_catalog_entry_change_request(
    request_id: int, service: CatalogEntryService = Depends(get_service)
):
    try:
        return CatalogChangeRequestResponse.from_entity(service.get_change_request(request_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/change-requests/{request_id}/approve",
    response_model=CatalogEntryResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def approve_catalog_entry_change(
    request_id: int,
    payload: CatalogChangeReviewRequest,
    service: CatalogEntryService = Depends(get_service),
):
    """Duyệt yêu cầu -- áp dụng thay đổi vào mục danh mục (tăng version

    + ghi lịch sử). (Dùng bởi UC-037.)"""
    try:
        entry = service.approve_change(
            request_id, reviewed_by=payload.reviewed_by, review_note=payload.review_note
        )
        return CatalogEntryResponse.from_entity(entry)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/change-requests/{request_id}/reject",
    response_model=CatalogChangeRequestResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_catalog_entry_change(
    request_id: int,
    payload: CatalogChangeReviewRequest,
    service: CatalogEntryService = Depends(get_service),
):
    try:
        request = service.reject_change(
            request_id, reviewed_by=payload.reviewed_by, review_note=payload.review_note
        )
        return CatalogChangeRequestResponse.from_entity(request)
    except DomainError as exc:
        raise _domain_error_to_http(exc)