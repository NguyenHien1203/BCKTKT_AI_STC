from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_org_unit_catalog import OrgUnitCatalogService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyOrgUnitCatalogRepository,
    SqlAlchemyOrgUnitCatalogVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CloseOrgUnitRequest,
    ErrorResponse,
    MergeOrgUnitRequest,
    MergeOrgUnitResponse,
    OrgUnitCatalogCreate,
    OrgUnitCatalogResponse,
    OrgUnitCatalogUpdate,
    OrgUnitCatalogVersionResponse,
    OrgUnitTreeNodeResponse,
    SplitOrgUnitRequest,
    SplitOrgUnitResponse,
)

router = APIRouter(prefix="/org-unit-catalog", tags=["UC-033 Quản lý danh mục đơn vị"])


def get_service(db: Session = Depends(get_db)) -> OrgUnitCatalogService:
    return OrgUnitCatalogService(
        unit_repo=SqlAlchemyOrgUnitCatalogRepository(db),
        version_repo=SqlAlchemyOrgUnitCatalogVersionRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "ALREADY_EXISTS" in exc.code or "ALREADY_CLOSED" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem danh mục đơn vị (cây phân cấp) ----------


@router.get("/tree", response_model=List[OrgUnitTreeNodeResponse])
def get_org_unit_tree(
    include_closed: bool = Query(True, description="True (mặc định) để gồm cả đơn vị đã đóng"),
    service: OrgUnitCatalogService = Depends(get_service),
):
    """Bước 1 'Xem danh mục đơn vị (cây phân cấp)' -- hệ thống hiển thị."""
    tree = service.get_tree(include_closed=include_closed)
    return [OrgUnitTreeNodeResponse.from_node(n) for n in tree]


@router.get("", response_model=List[OrgUnitCatalogResponse])
def list_org_units(
    parent_id: Optional[int] = Query(None, description="Lọc theo đơn vị cha (bỏ trống = tất cả)"),
    only_root: bool = Query(False, description="True để chỉ lấy các đơn vị gốc của cây"),
    unit_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="ACTIVE hoặc CLOSED"),
    service: OrgUnitCatalogService = Depends(get_service),
):
    if only_root:
        resolved_parent_id: Optional[int] = None
    elif parent_id is not None:
        resolved_parent_id = parent_id
    else:
        resolved_parent_id = "__unset__"
    units = service.list_units(parent_id=resolved_parent_id, unit_type=unit_type, status=status)
    return [OrgUnitCatalogResponse.from_entity(u) for u in units]


@router.get(
    "/{unit_id}",
    response_model=OrgUnitCatalogResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_org_unit(unit_id: int, service: OrgUnitCatalogService = Depends(get_service)):
    try:
        return OrgUnitCatalogResponse.from_entity(service.get(unit_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{unit_id}/versions",
    response_model=List[OrgUnitCatalogVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_org_unit_versions(unit_id: int, service: OrgUnitCatalogService = Depends(get_service)):
    try:
        versions = service.list_versions(unit_id)
        return [OrgUnitCatalogVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Thêm đơn vị mới ----------


@router.post(
    "",
    response_model=OrgUnitCatalogResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_org_unit(
    payload: OrgUnitCatalogCreate, service: OrgUnitCatalogService = Depends(get_service)
):
    """Bước 2 'Thêm đơn vị mới' -- hệ thống kiểm tra trùng mã + lưu

    phiên bản."""
    try:
        unit = service.create_unit(
            code=payload.code,
            name=payload.name,
            unit_type=payload.unit_type,
            parent_id=payload.parent_id,
            effective_from=payload.effective_from,
            note=payload.note,
        )
        return OrgUnitCatalogResponse.from_entity(unit)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Sửa thông tin đơn vị ----------


@router.put(
    "/{unit_id}",
    response_model=OrgUnitCatalogResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_org_unit(
    unit_id: int,
    payload: OrgUnitCatalogUpdate,
    service: OrgUnitCatalogService = Depends(get_service),
):
    """Bước 3 'Sửa thông tin đơn vị' -- hệ thống lưu (tăng version + ghi

    lịch sử phiên bản)."""
    try:
        parent_id: object = payload.parent_id
        if payload.clear_parent:
            parent_id = None
        elif payload.parent_id is None:
            parent_id = "__unset__"
        unit = service.update_unit(
            unit_id,
            name=payload.name,
            unit_type=payload.unit_type,
            parent_id=parent_id,
            note=payload.note,
        )
        return OrgUnitCatalogResponse.from_entity(unit)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 4: Đóng / Tách / Sáp nhập đơn vị (lifecycle) ----------


@router.post(
    "/{unit_id}/close",
    response_model=OrgUnitCatalogResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def close_org_unit(
    unit_id: int,
    payload: CloseOrgUnitRequest,
    service: OrgUnitCatalogService = Depends(get_service),
):
    """Đóng đơn vị -- hệ thống lưu `effective_to`."""
    try:
        unit = service.close_unit(unit_id, effective_to=payload.effective_to, note=payload.note)
        return OrgUnitCatalogResponse.from_entity(unit)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{unit_id}/split",
    response_model=SplitOrgUnitResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def split_org_unit(
    unit_id: int,
    payload: SplitOrgUnitRequest,
    service: OrgUnitCatalogService = Depends(get_service),
):
    """Tách đơn vị -- hệ thống lưu `effective_from`/`effective_to`."""
    try:
        result = service.split_unit(
            unit_id,
            effective_from=payload.effective_from,
            new_units=[u.model_dump() for u in payload.new_units],
            note=payload.note,
        )
        return SplitOrgUnitResponse.from_result(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/merge",
    response_model=MergeOrgUnitResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def merge_org_units(
    payload: MergeOrgUnitRequest, service: OrgUnitCatalogService = Depends(get_service)
):
    """Sáp nhập đơn vị -- hệ thống lưu `effective_from`/`effective_to`."""
    try:
        result = service.merge_units(
            source_unit_ids=payload.source_unit_ids,
            target=payload.target.model_dump(),
            effective_from=payload.effective_from,
            note=payload.note,
        )
        return MergeOrgUnitResponse.from_result(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)