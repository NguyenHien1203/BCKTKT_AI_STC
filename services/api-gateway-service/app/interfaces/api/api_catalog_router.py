"""UC-058 — Quản lý danh mục API.

Prefix `/api-catalog`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_api_catalog import ApiCatalogService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyApiCatalogRepository,
    SqlAlchemyApiCatalogVersionHistoryRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ApiCatalogEntryCreate,
    ApiCatalogEntryResponse,
    ApiCatalogVersionConfigure,
    ApiCatalogVersionHistoryResponse,
)

router = APIRouter(prefix="/api-catalog", tags=["UC-058 - Danh mục API"])


def _service(db: Session = Depends(get_db)) -> ApiCatalogService:
    return ApiCatalogService(
        catalog_repo=SqlAlchemyApiCatalogRepository(db),
        version_repo=SqlAlchemyApiCatalogVersionHistoryRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "API_CATALOG_ENTRY_NOT_FOUND": 404,
        "API_CATALOG_CODE_ALREADY_EXISTS": 409,
        "API_CATALOG_ENTRY_ALREADY_UNPUBLISHED": 409,
        "API_CATALOG_ENTRY_ALREADY_PUBLISHED": 409,
        "INVALID_API_CATALOG_ENTRY": 422,
        "INVALID_API_CATALOG_VERSION_CONFIG": 422,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=ApiCatalogEntryResponse, status_code=201)
def publish_api(
    payload: ApiCatalogEntryCreate,
    service: ApiCatalogService = Depends(_service),
):
    """Bước 1 — Publish API mới (Search/QA/Data/Metadata) -> hệ thống cập
    nhật danh mục."""
    try:
        entry = service.publish_api(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            api_type=payload.api_type,
            endpoint_path=payload.endpoint_path,
            version=payload.version,
            sunset_date=payload.sunset_date,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc
    return entry


@router.get("", response_model=list[ApiCatalogEntryResponse])
def list_api_catalog(
    api_type: Optional[str] = None,
    status: Optional[str] = None,
    service: ApiCatalogService = Depends(_service),
):
    return service.list_catalog(api_type=api_type, status=status)


@router.get("/{entry_id}", response_model=ApiCatalogEntryResponse)
def get_api_catalog_entry(
    entry_id: int,
    service: ApiCatalogService = Depends(_service),
):
    try:
        return service.get(entry_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get(
    "/{entry_id}/versions",
    response_model=list[ApiCatalogVersionHistoryResponse],
)
def list_api_catalog_versions(
    entry_id: int,
    service: ApiCatalogService = Depends(_service),
):
    try:
        return service.list_versions(entry_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.post("/{entry_id}/unpublish", response_model=ApiCatalogEntryResponse)
def unpublish_api(
    entry_id: int,
    service: ApiCatalogService = Depends(_service),
):
    """Bước 2 — Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối."""
    try:
        return service.unpublish_api(entry_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.post("/{entry_id}/republish", response_model=ApiCatalogEntryResponse)
def republish_api(
    entry_id: int,
    service: ApiCatalogService = Depends(_service),
):
    """Công bố lại 1 API đã gỡ công bố (đối xứng với bước 2)."""
    try:
        return service.republish_api(entry_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.put("/{entry_id}/version", response_model=ApiCatalogEntryResponse)
def configure_api_version(
    entry_id: int,
    payload: ApiCatalogVersionConfigure,
    service: ApiCatalogService = Depends(_service),
):
    """Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống
    lưu."""
    try:
        return service.configure_version(
            entry_id=entry_id,
            version=payload.version,
            sunset_date=payload.sunset_date,
            change_note=payload.change_note,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc