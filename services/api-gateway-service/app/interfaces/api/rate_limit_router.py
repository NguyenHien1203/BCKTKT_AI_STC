"""UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.

Prefix `/service-tiers`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_rate_limit import RateLimitService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyBurstPolicyRepository,
    SqlAlchemyRateLimitPolicyRepository,
    SqlAlchemyServiceTierRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    BurstPolicyConfigure,
    BurstPolicyResponse,
    RateLimitPolicyConfigure,
    RateLimitPolicyResponse,
    ServiceTierCreate,
    ServiceTierResponse,
    ServiceTierUpdate,
)

router = APIRouter(prefix="/service-tiers", tags=["UC-060 - Quản lý giới hạn tần suất + gói dịch vụ"])


def _service(db: Session = Depends(get_db)) -> RateLimitService:
    return RateLimitService(
        tier_repo=SqlAlchemyServiceTierRepository(db),
        rate_limit_repo=SqlAlchemyRateLimitPolicyRepository(db),
        burst_repo=SqlAlchemyBurstPolicyRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "SERVICE_TIER_NOT_FOUND": 404,
        "SERVICE_TIER_CODE_ALREADY_EXISTS": 409,
        "INVALID_SERVICE_TIER": 422,
        "RATE_LIMIT_POLICY_NOT_FOUND": 404,
        "INVALID_RATE_LIMIT_POLICY": 422,
        "BURST_POLICY_NOT_FOUND": 404,
        "INVALID_BURST_POLICY": 422,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


# ---------------------------------------------------------------------------
# Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
# ---------------------------------------------------------------------------
@router.post("", response_model=ServiceTierResponse, status_code=201)
def create_service_tier(
    payload: ServiceTierCreate,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.create_tier(
            code=payload.code,
            name=payload.name,
            description=payload.description,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get("", response_model=list[ServiceTierResponse])
def list_service_tiers(
    is_active: Optional[bool] = None,
    service: RateLimitService = Depends(_service),
):
    return service.list_tiers(is_active=is_active)


@router.get("/{tier_id}", response_model=ServiceTierResponse)
def get_service_tier(
    tier_id: int,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.get_tier(tier_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.put("/{tier_id}", response_model=ServiceTierResponse)
def update_service_tier(
    tier_id: int,
    payload: ServiceTierUpdate,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.update_tier(
            tier_id=tier_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


# ---------------------------------------------------------------------------
# Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) -> hệ
# thống áp dụng tại Cổng API.
# ---------------------------------------------------------------------------
@router.put("/{tier_id}/rate-limit", response_model=RateLimitPolicyResponse)
def configure_rate_limit(
    tier_id: int,
    payload: RateLimitPolicyConfigure,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.configure_rate_limit(
            tier_id=tier_id,
            requests_per_second=payload.requests_per_second,
            requests_per_day=payload.requests_per_day,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get("/{tier_id}/rate-limit", response_model=RateLimitPolicyResponse)
def get_rate_limit(
    tier_id: int,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.get_rate_limit(tier_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


# ---------------------------------------------------------------------------
# Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ thống
# lưu.
# ---------------------------------------------------------------------------
@router.put("/{tier_id}/burst-policy", response_model=BurstPolicyResponse)
def configure_burst_policy(
    tier_id: int,
    payload: BurstPolicyConfigure,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.configure_burst_policy(
            tier_id=tier_id,
            burst_limit=payload.burst_limit,
            window_seconds=payload.window_seconds,
            throttle_policy=payload.throttle_policy,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get("/{tier_id}/burst-policy", response_model=BurstPolicyResponse)
def get_burst_policy(
    tier_id: int,
    service: RateLimitService = Depends(_service),
):
    try:
        return service.get_burst_policy(tier_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc