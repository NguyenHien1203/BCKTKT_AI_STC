"""UC-059 — Quản lý API key.

Flow:
  (1) Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá + phạm vi.
  (2) Thu hồi khoá API -> hệ thống thu hồi.
  (3) Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo khoá mới
      + thời gian ân hạn.
  (4) Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.domain.entities import ApiKey, ApiKeyUsageLog
from app.domain.exceptions import (
    ApiKeyAlreadyRevoked,
    ApiKeyNotActive,
    ApiKeyNotFound,
    InvalidApiKey,
    InvalidApiKeyRotation,
)
from app.domain.repositories import ApiKeyRepository, ApiKeyUsageLogRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ApiKeyService:
    def __init__(
        self,
        key_repo: ApiKeyRepository,
        usage_log_repo: ApiKeyUsageLogRepository,
    ) -> None:
        self._key_repo = key_repo
        self._usage_log_repo = usage_log_repo

    # ------------------------------------------------------------------
    # Bước 1 — Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá +
    # phạm vi.
    # ------------------------------------------------------------------
    def create_key(
        self,
        consumer_name: str,
        consumer_code: str,
        description: str,
        scope: str,
        service_tier_code: Optional[str] = None,
    ) -> Tuple[ApiKey, str]:
        try:
            entry, raw_key = ApiKey.create(
                consumer_name=consumer_name,
                consumer_code=consumer_code,
                description=description,
                scope=scope,
                when=_now(),
            )
            entry.service_tier_code = service_tier_code
        except ValueError as exc:
            raise InvalidApiKey(str(exc)) from exc

        saved = self._key_repo.add(entry)
        return saved, raw_key

    # ------------------------------------------------------------------
    # Bước 2 — Thu hồi khoá API -> hệ thống thu hồi.
    # ------------------------------------------------------------------
    def revoke_key(self, key_id: int) -> ApiKey:
        api_key = self._get_or_raise(key_id)
        try:
            api_key.revoke(_now())
        except ValueError as exc:
            raise ApiKeyAlreadyRevoked(key_id) from exc
        return self._key_repo.update(api_key)

    # ------------------------------------------------------------------
    # Bước 3 — Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo
    # khoá mới + thời gian ân hạn.
    # ------------------------------------------------------------------
    def rotate_key(
        self,
        key_id: int,
        grace_period_days: Optional[int] = None,
        rotation_mode: str = "MANUAL",
    ) -> Tuple[ApiKey, ApiKey, str]:
        """Trả về (khoá_cũ_đã_ROTATED, khoá_mới, raw_key_mới)."""
        if rotation_mode not in ("MANUAL", "AUTO"):
            raise InvalidApiKeyRotation(
                f"Phương thức luân chuyển '{rotation_mode}' không hợp lệ, "
                "phải là MANUAL hoặc AUTO"
            )

        old_key = self._get_or_raise(key_id)
        if grace_period_days is None:
            grace_period_days = ApiKey.DEFAULT_GRACE_PERIOD_DAYS

        now = _now()
        try:
            new_entry, raw_key = ApiKey.create(
                consumer_name=old_key.consumer_name,
                consumer_code=old_key.consumer_code,
                description=old_key.description,
                scope=old_key.scope,
                when=now,
                previous_key_id=old_key.id,
            )
            new_entry.service_tier_code = old_key.service_tier_code
        except ValueError as exc:
            raise InvalidApiKeyRotation(str(exc)) from exc
        new_key = self._key_repo.add(new_entry)

        try:
            old_key.mark_rotated(
                when=now,
                grace_period_days=grace_period_days,
                new_key_id=new_key.id,
            )
        except ValueError as exc:
            raise ApiKeyNotActive(key_id) from exc
        updated_old_key = self._key_repo.update(old_key)

        self._log(
            api_key_id=updated_old_key.id,
            endpoint_path="/api-keys/{}/rotate".format(key_id),
            method="POST",
            status_code=200,
            note=(
                f"Luân chuyển khoá API ({rotation_mode}) -> khoá mới #{new_key.id}, "
                f"ân hạn {grace_period_days} ngày"
            ),
            when=now,
        )

        return updated_old_key, new_key, raw_key

    # ------------------------------------------------------------------
    # Bước 4 — Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký.
    # ------------------------------------------------------------------
    def log_usage(
        self,
        key_id: int,
        endpoint_path: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        consumer_ip: Optional[str] = None,
        note: str = "",
    ) -> ApiKeyUsageLog:
        self._get_or_raise(key_id)
        if not endpoint_path or not endpoint_path.strip():
            raise InvalidApiKey("Đường dẫn điểm cuối (endpoint) không được để trống")
        return self._log(
            api_key_id=key_id,
            endpoint_path=endpoint_path,
            method=method,
            status_code=status_code,
            consumer_ip=consumer_ip,
            note=note,
            when=_now(),
        )

    def list_usage_logs(self, key_id: int, limit: int = 100) -> List[ApiKeyUsageLog]:
        self._get_or_raise(key_id)
        return self._usage_log_repo.list_for_key(key_id, limit=limit)

    # ------------------------------------------------------------------
    # Truy vấn
    # ------------------------------------------------------------------
    def get(self, key_id: int) -> ApiKey:
        return self._get_or_raise(key_id)

    def list_keys(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiKey]:
        return self._key_repo.list(consumer_code=consumer_code, status=status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_or_raise(self, key_id: int) -> ApiKey:
        api_key = self._key_repo.get_by_id(key_id)
        if api_key is None:
            raise ApiKeyNotFound(key_id)
        return api_key

    def _log(
        self,
        api_key_id: int,
        endpoint_path: str,
        method: str,
        when: datetime,
        status_code: Optional[int] = None,
        consumer_ip: Optional[str] = None,
        note: str = "",
    ) -> ApiKeyUsageLog:
        return self._usage_log_repo.add(
            ApiKeyUsageLog(
                id=None,
                api_key_id=api_key_id,
                endpoint_path=endpoint_path,
                method=method,
                status_code=status_code,
                consumer_ip=consumer_ip,
                note=note,
                called_at=when,
            )
        )