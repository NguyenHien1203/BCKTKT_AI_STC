from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_credential_asset import (
    DEFAULT_EXPIRY_ALERT_DAYS_AHEAD,
    CredentialAssetService,
)
from app.domain.exceptions import DomainError
from app.infrastructure.alert_sender import NoOpAlertmanagerAlertSender
from app.infrastructure.credential_crypto import SimpleCredentialCrypto
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCredentialAssetRepository,
    SqlAlchemySourceConnectionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CredentialAssetCreate,
    CredentialAssetResponse,
    CredentialAssetRotate,
    ErrorResponse,
    ExpiryAlertResult,
)

router = APIRouter(prefix="/credential-assets", tags=["UC-017 Certificate/API key + cảnh báo hết hạn"])

_crypto = SimpleCredentialCrypto()
_alert_sender = NoOpAlertmanagerAlertSender()


def get_service(db: Session = Depends(get_db)) -> CredentialAssetService:
    return CredentialAssetService(
        asset_repo=SqlAlchemyCredentialAssetRepository(db),
        connection_repo=SqlAlchemySourceConnectionRepository(db),
        crypto=_crypto,
        alert_sender=_alert_sender,
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "",
    response_model=CredentialAssetResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def register_credential_asset(
    payload: CredentialAssetCreate, service: CredentialAssetService = Depends(get_service)
):
    """Quản lý certificate/API key của bộ kết nối: đăng ký mới."""
    try:
        return service.register(
            connection_id=payload.connection_id,
            asset_type=payload.asset_type,
            secret_value=payload.secret_value,
            expires_at=payload.expires_at,
            rotation_period_days=payload.rotation_period_days,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[CredentialAssetResponse])
def list_credential_assets(
    connection_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    only_active: bool = Query(False),
    service: CredentialAssetService = Depends(get_service),
):
    return service.list_assets(
        connection_id=connection_id, asset_type=asset_type, only_active=only_active
    )


@router.get(
    "/{asset_id}",
    response_model=CredentialAssetResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_credential_asset(asset_id: int, service: CredentialAssetService = Depends(get_service)):
    try:
        return service.get(asset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{asset_id}/rotate",
    response_model=CredentialAssetResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def rotate_credential_asset(
    asset_id: int,
    payload: CredentialAssetRotate,
    service: CredentialAssetService = Depends(get_service),
):
    """Luân chuyển (rotate) certificate/API key: hệ thống lưu lịch luân chuyển."""
    try:
        return service.rotate(asset_id, payload.secret_value, payload.expires_at)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{asset_id}/deactivate",
    response_model=CredentialAssetResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_credential_asset(
    asset_id: int, service: CredentialAssetService = Depends(get_service)
):
    try:
        return service.deactivate(asset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{asset_id}/activate",
    response_model=CredentialAssetResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_credential_asset(
    asset_id: int, service: CredentialAssetService = Depends(get_service)
):
    try:
        return service.activate(asset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/check-expiring", response_model=List[ExpiryAlertResult])
def check_expiring_credentials(
    days_ahead: int = Query(DEFAULT_EXPIRY_ALERT_DAYS_AHEAD, gt=0),
    service: CredentialAssetService = Depends(get_service),
):
    """Nhận cảnh báo trước khi thông tin xác thực hết hạn: quét
    certificate/API key sắp hết hạn trong `days_ahead` ngày tới và gửi
    cảnh báo qua Alertmanager cho từng cái."""
    return service.check_expiring(days_ahead)