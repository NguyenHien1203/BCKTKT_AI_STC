"""UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.

Flow:
  (1) Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
  (2) Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) -> hệ thống
      áp dụng tại Cổng API.
  (3) Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ thống lưu.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import BurstPolicy, RateLimitPolicy, ServiceTier
from app.domain.exceptions import (
    BurstPolicyNotFound,
    InvalidBurstPolicy,
    InvalidRateLimitPolicy,
    InvalidServiceTier,
    RateLimitPolicyNotFound,
    ServiceTierCodeAlreadyExists,
    ServiceTierNotFound,
)
from app.domain.repositories import (
    BurstPolicyRepository,
    RateLimitPolicyRepository,
    ServiceTierRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RateLimitService:
    def __init__(
        self,
        tier_repo: ServiceTierRepository,
        rate_limit_repo: RateLimitPolicyRepository,
        burst_repo: BurstPolicyRepository,
    ) -> None:
        self._tier_repo = tier_repo
        self._rate_limit_repo = rate_limit_repo
        self._burst_repo = burst_repo

    # ------------------------------------------------------------------
    # Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống
    # lưu.
    # ------------------------------------------------------------------
    def create_tier(self, code: str, name: str, description: str = "") -> ServiceTier:
        if self._tier_repo.get_by_code(code) is not None:
            raise ServiceTierCodeAlreadyExists(code)
        try:
            tier = ServiceTier(
                id=None,
                code=code,
                name=name,
                description=description,
                is_active=True,
                created_at=_now(),
            )
        except ValueError as exc:
            raise InvalidServiceTier(str(exc)) from exc
        return self._tier_repo.add(tier)

    def update_tier(
        self,
        tier_id: int,
        name: str,
        description: str = "",
        is_active: Optional[bool] = None,
    ) -> ServiceTier:
        tier = self._get_tier_or_raise(tier_id)
        try:
            tier.rename(name=name, description=description)
        except ValueError as exc:
            raise InvalidServiceTier(str(exc)) from exc
        if is_active is not None:
            tier.set_active(is_active)
        tier.updated_at = _now()
        return self._tier_repo.update(tier)

    def get_tier(self, tier_id: int) -> ServiceTier:
        return self._get_tier_or_raise(tier_id)

    def list_tiers(self, is_active: Optional[bool] = None) -> List[ServiceTier]:
        return self._tier_repo.list(is_active=is_active)

    # ------------------------------------------------------------------
    # Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) ->
    # hệ thống áp dụng tại Cổng API.
    # ------------------------------------------------------------------
    def configure_rate_limit(
        self,
        tier_id: int,
        requests_per_second: int,
        requests_per_day: int,
    ) -> RateLimitPolicy:
        self._get_tier_or_raise(tier_id)
        now = _now()
        existing = self._rate_limit_repo.get_by_tier_id(tier_id)
        try:
            if existing is None:
                policy = RateLimitPolicy(
                    id=None,
                    tier_id=tier_id,
                    requests_per_second=requests_per_second,
                    requests_per_day=requests_per_day,
                    created_at=now,
                )
                policy.apply(now)
                return self._rate_limit_repo.add(policy)

            existing.reconfigure(
                requests_per_second=requests_per_second,
                requests_per_day=requests_per_day,
            )
            existing.apply(now)
            existing.updated_at = now
            return self._rate_limit_repo.update(existing)
        except ValueError as exc:
            raise InvalidRateLimitPolicy(str(exc)) from exc

    def get_rate_limit(self, tier_id: int) -> RateLimitPolicy:
        self._get_tier_or_raise(tier_id)
        policy = self._rate_limit_repo.get_by_tier_id(tier_id)
        if policy is None:
            raise RateLimitPolicyNotFound(tier_id)
        return policy

    # ------------------------------------------------------------------
    # Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ
    # thống lưu.
    # ------------------------------------------------------------------
    def configure_burst_policy(
        self,
        tier_id: int,
        burst_limit: int,
        window_seconds: int,
        throttle_policy: str,
    ) -> BurstPolicy:
        self._get_tier_or_raise(tier_id)
        now = _now()
        existing = self._burst_repo.get_by_tier_id(tier_id)
        try:
            if existing is None:
                policy = BurstPolicy(
                    id=None,
                    tier_id=tier_id,
                    burst_limit=burst_limit,
                    window_seconds=window_seconds,
                    throttle_policy=throttle_policy,
                    created_at=now,
                )
                return self._burst_repo.add(policy)

            existing.reconfigure(
                burst_limit=burst_limit,
                window_seconds=window_seconds,
                throttle_policy=throttle_policy,
            )
            existing.updated_at = now
            return self._burst_repo.update(existing)
        except ValueError as exc:
            raise InvalidBurstPolicy(str(exc)) from exc

    def get_burst_policy(self, tier_id: int) -> BurstPolicy:
        self._get_tier_or_raise(tier_id)
        policy = self._burst_repo.get_by_tier_id(tier_id)
        if policy is None:
            raise BurstPolicyNotFound(tier_id)
        return policy

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_tier_or_raise(self, tier_id: int) -> ServiceTier:
        tier = self._tier_repo.get_by_id(tier_id)
        if tier is None:
            raise ServiceTierNotFound(tier_id)
        return tier