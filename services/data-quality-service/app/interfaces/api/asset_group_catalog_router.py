from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_asset_group_catalog import AssetGroupCatalogService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyAssetDepreciationRateRepository,
    SqlAlchemyAssetGroupCatalogRepository,
    SqlAlchemyAssetGroupCatalogVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    AssetDepreciationRateDeclare,
    AssetDepreciationRateResponse,
    AssetGroupCatalogCreate,
    AssetGroupCatalogResponse,
    AssetGroupCatalogUpdate,
    AssetGroupCatalogVersionResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/asset-group-catalog", tags=["UC-035 Quản lý danh mục nhóm tài sản"])


def get_service(db: Session = Depends(get_db)) -> AssetGroupCatalogService:
    return AssetGroupCatalogService(
        group_repo=SqlAlchemyAssetGroupCatalogRepository(db),
        version_repo=SqlAlchemyAssetGroupCatalogVersionRepository(db),
        rate_repo=SqlAlchemyAssetDepreciationRateRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "EXISTS" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem danh mục nhóm tài sản (TT 48 / TT 162) ----------


@router.get("", response_model=List[AssetGroupCatalogResponse])
def list_asset_groups(
    regulation: Optional[str] = Query(None, description="Lọc theo văn bản căn cứ: TT45 / TT162"),
    status: Optional[str] = Query(None, description="ACTIVE hoặc CLOSED"),
    service: AssetGroupCatalogService = Depends(get_service),
):
    """Bước 1 'Xem danh mục nhóm tài sản (TT 48 / TT 162)' -- hệ thống hiển thị."""
    groups = service.list_groups(regulation=regulation, status=status)
    return [AssetGroupCatalogResponse.from_entity(g) for g in groups]


@router.get(
    "/{group_id}",
    response_model=AssetGroupCatalogResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_asset_group(group_id: int, service: AssetGroupCatalogService = Depends(get_service)):
    try:
        return AssetGroupCatalogResponse.from_entity(service.get(group_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{group_id}/versions",
    response_model=List[AssetGroupCatalogVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_asset_group_versions(
    group_id: int, service: AssetGroupCatalogService = Depends(get_service)
):
    try:
        versions = service.list_versions(group_id)
        return [AssetGroupCatalogVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Thêm / Sửa entry (hệ thống quản lý phiên bản) ----------


@router.post(
    "",
    response_model=AssetGroupCatalogResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_asset_group(
    payload: AssetGroupCatalogCreate, service: AssetGroupCatalogService = Depends(get_service)
):
    """Bước 2 'Thêm entry' -- hệ thống quản lý phiên bản (version=1)."""
    try:
        group = service.create_group(
            code=payload.code,
            name=payload.name,
            regulation=payload.regulation,
            useful_life_years=payload.useful_life_years,
            effective_from=payload.effective_from,
            note=payload.note,
        )
        return AssetGroupCatalogResponse.from_entity(group)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{group_id}",
    response_model=AssetGroupCatalogResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_asset_group(
    group_id: int,
    payload: AssetGroupCatalogUpdate,
    service: AssetGroupCatalogService = Depends(get_service),
):
    """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản (tăng version +

    ghi lịch sử)."""
    useful_life_years = "__unset__"
    if payload.clear_useful_life_years:
        useful_life_years = None
    elif payload.useful_life_years is not None:
        useful_life_years = payload.useful_life_years
    try:
        group = service.update_group(
            group_id,
            name=payload.name,
            regulation=payload.regulation,
            useful_life_years=useful_life_years,
            status=payload.status,
            note=payload.note,
        )
        return AssetGroupCatalogResponse.from_entity(group)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Khai báo tỉ lệ khấu hao theo nhóm ----------


@router.post(
    "/{group_id}/depreciation-rates",
    response_model=AssetDepreciationRateResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def declare_asset_depreciation_rate(
    group_id: int,
    payload: AssetDepreciationRateDeclare,
    service: AssetGroupCatalogService = Depends(get_service),
):
    """Bước 3 'Khai báo tỉ lệ khấu hao theo nhóm' -- hệ thống lưu."""
    try:
        rate = service.declare_depreciation_rate(
            group_id,
            depreciation_rate_percent=payload.depreciation_rate_percent,
            useful_life_years=payload.useful_life_years,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            note=payload.note,
            declared_by=payload.declared_by,
        )
        return AssetDepreciationRateResponse.from_entity(rate)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{group_id}/depreciation-rates",
    response_model=List[AssetDepreciationRateResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_asset_depreciation_rates(
    group_id: int, service: AssetGroupCatalogService = Depends(get_service)
):
    try:
        rates = service.list_depreciation_rates(group_id)
        return [AssetDepreciationRateResponse.from_entity(r) for r in rates]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{group_id}/depreciation-rates/current",
    response_model=Optional[AssetDepreciationRateResponse],
    responses={404: {"model": ErrorResponse}},
)
def get_current_asset_depreciation_rate(
    group_id: int, service: AssetGroupCatalogService = Depends(get_service)
):
    try:
        rate = service.get_current_depreciation_rate(group_id)
        return AssetDepreciationRateResponse.from_entity(rate) if rate else None
    except DomainError as exc:
        raise _domain_error_to_http(exc)