"""UC-059 — Quản lý API key.

Prefix `/api-keys`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_api_key import ApiKeyService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyApiKeyUsageLogRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyRotateRequest,
    ApiKeyRotateResponse,
    ApiKeyUsageLogCreate,
    ApiKeyUsageLogResponse,
)

router = APIRouter(prefix="/api-keys", tags=["UC-059 - Quản lý API key"])


def _service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(
        key_repo=SqlAlchemyApiKeyRepository(db),
        usage_log_repo=SqlAlchemyApiKeyUsageLogRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "API_KEY_NOT_FOUND": 404,
        "API_KEY_ALREADY_REVOKED": 409,
        "API_KEY_NOT_ACTIVE": 409,
        "INVALID_API_KEY": 422,
        "INVALID_API_KEY_ROTATION": 422,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    service: ApiKeyService = Depends(_service),
):
    """Bước 1 — Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá +
    phạm vi. `raw_key` chỉ được trả về DUY NHẤT ở response này."""
    try:
        api_key, raw_key = service.create_key(
            consumer_name=payload.consumer_name,
            consumer_code=payload.consumer_code,
            description=payload.description,
            scope=payload.scope,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc
    return ApiKeyCreatedResponse(raw_key=raw_key, **ApiKeyResponse.model_validate(api_key).model_dump())


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    consumer_code: Optional[str] = None,
    status: Optional[str] = None,
    service: ApiKeyService = Depends(_service),
):
    return service.list_keys(consumer_code=consumer_code, status=status)


@router.get("/{key_id}", response_model=ApiKeyResponse)
def get_api_key(
    key_id: int,
    service: ApiKeyService = Depends(_service),
):
    try:
        return service.get(key_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse)
def revoke_api_key(
    key_id: int,
    service: ApiKeyService = Depends(_service),
):
    """Bước 2 — Thu hồi khoá API -> hệ thống thu hồi."""
    try:
        return service.revoke_key(key_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.post("/{key_id}/rotate", response_model=ApiKeyRotateResponse)
def rotate_api_key(
    key_id: int,
    payload: ApiKeyRotateRequest,
    service: ApiKeyService = Depends(_service),
):
    """Bước 3 — Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo
    khoá mới + thời gian ân hạn. `new_key.raw_key` chỉ trả về DUY NHẤT ở
    response này."""
    try:
        old_key, new_key, raw_key = service.rotate_key(
            key_id=key_id,
            grace_period_days=payload.grace_period_days,
            rotation_mode=payload.rotation_mode,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc
    return ApiKeyRotateResponse(
        old_key=ApiKeyResponse.model_validate(old_key),
        new_key=ApiKeyCreatedResponse(
            raw_key=raw_key, **ApiKeyResponse.model_validate(new_key).model_dump()
        ),
    )


@router.post(
    "/{key_id}/usage-logs",
    response_model=ApiKeyUsageLogResponse,
    status_code=201,
)
def log_api_key_usage(
    key_id: int,
    payload: ApiKeyUsageLogCreate,
    service: ApiKeyService = Depends(_service),
):
    """Bước 4 — Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký."""
    try:
        return service.log_usage(
            key_id=key_id,
            endpoint_path=payload.endpoint_path,
            method=payload.method,
            status_code=payload.status_code,
            consumer_ip=payload.consumer_ip,
            note=payload.note,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get("/{key_id}/usage-logs", response_model=list[ApiKeyUsageLogResponse])
def list_api_key_usage_logs(
    key_id: int,
    limit: int = 100,
    service: ApiKeyService = Depends(_service),
):
    try:
        return service.list_usage_logs(key_id, limit=limit)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc