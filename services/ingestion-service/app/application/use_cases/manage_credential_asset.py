"""Application layer — UC-017 (phần 2/2): Quản lý certificate/API key.

Luồng nghiệp vụ còn lại của UC-017:
3. Quản lý certificate/API key của bộ kết nối -> hệ thống lưu lịch luân
   chuyển (mỗi lần rotate lưu lại bản ghi lịch sử).
4. Nhận cảnh báo trước khi thông tin xác thực hết hạn -> hệ thống
   Alertmanager gửi cảnh báo (qua cổng `CredentialAlertSender`).
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import CredentialAsset
from app.domain.exceptions import (
    CredentialAssetNotFound,
    InvalidCredentialAsset,
    SourceConnectionNotFound,
)
from app.domain.repositories import (
    CredentialAlertSender,
    CredentialAssetRepository,
    CredentialCrypto,
    SourceConnectionRepository,
)

DEFAULT_EXPIRY_ALERT_DAYS_AHEAD = 30


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CredentialAssetService:
    def __init__(
        self,
        asset_repo: CredentialAssetRepository,
        connection_repo: SourceConnectionRepository,
        crypto: CredentialCrypto,
        alert_sender: CredentialAlertSender,
    ):
        self._assets = asset_repo
        self._connections = connection_repo
        self._crypto = crypto
        self._alert_sender = alert_sender

    def register(
        self,
        connection_id: int,
        asset_type: str,
        secret_value: str,
        expires_at: str,
        rotation_period_days: int = 90,
        issued_at: Optional[str] = None,
    ) -> CredentialAsset:
        """Quản lý certificate/API key của bộ kết nối: đăng ký mới, lưu giá
        trị đã mã hoá + lịch luân chuyển bắt đầu rỗng."""
        if self._connections.get_by_id(connection_id) is None:
            raise SourceConnectionNotFound(connection_id)

        if not secret_value or not secret_value.strip():
            raise InvalidCredentialAsset("Giá trị certificate/API key không được để trống")

        try:
            asset = CredentialAsset(
                id=None,
                connection_id=connection_id,
                asset_type=asset_type,
                encrypted_value=self._crypto.encrypt(secret_value),
                issued_at=issued_at or _utc_now_iso(),
                expires_at=expires_at,
                rotation_period_days=rotation_period_days,
            )
        except ValueError as exc:
            raise InvalidCredentialAsset(str(exc)) from exc

        return self._assets.add(asset)

    def get(self, asset_id: int) -> CredentialAsset:
        asset = self._assets.get_by_id(asset_id)
        if asset is None:
            raise CredentialAssetNotFound(asset_id)
        return asset

    def list_assets(
        self,
        connection_id: Optional[int] = None,
        asset_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[CredentialAsset]:
        return self._assets.list(
            connection_id=connection_id, asset_type=asset_type, only_active=only_active
        )

    def rotate(self, asset_id: int, new_secret_value: str, new_expires_at: str) -> CredentialAsset:
        """Luân chuyển certificate/API key: hệ thống lưu lịch luân chuyển."""
        asset = self.get(asset_id)
        if not new_secret_value or not new_secret_value.strip():
            raise InvalidCredentialAsset("Giá trị certificate/API key mới không được để trống")
        try:
            asset.rotate(
                new_encrypted_value=self._crypto.encrypt(new_secret_value),
                new_expires_at=new_expires_at,
                rotated_at=_utc_now_iso(),
            )
        except ValueError as exc:
            raise InvalidCredentialAsset(str(exc)) from exc
        return self._assets.update(asset)

    def deactivate(self, asset_id: int) -> CredentialAsset:
        asset = self.get(asset_id)
        asset.deactivate()
        return self._assets.update(asset)

    def activate(self, asset_id: int) -> CredentialAsset:
        asset = self.get(asset_id)
        asset.activate()
        return self._assets.update(asset)

    def check_expiring(self, days_ahead: int = DEFAULT_EXPIRY_ALERT_DAYS_AHEAD) -> List[dict]:
        """Nhận cảnh báo trước khi thông tin xác thực hết hạn: quét các
        certificate/API key còn hoạt động sắp hết hạn trong `days_ahead`
        ngày tới, gửi cảnh báo qua Alertmanager cho từng cái và trả về kết
        quả gửi."""
        now = datetime.now(timezone.utc)
        results = []
        for asset in self._assets.list(only_active=True):
            if not asset.is_expiring_within(days_ahead, now):
                continue
            days_remaining = asset.days_until_expiry(now)
            sent, message = self._alert_sender.send_expiry_alert(
                asset_type=asset.asset_type,
                connection_id=asset.connection_id,
                expires_at=asset.expires_at,
                days_remaining=days_remaining,
            )
            results.append(
                {
                    "asset_id": asset.id,
                    "connection_id": asset.connection_id,
                    "asset_type": asset.asset_type,
                    "expires_at": asset.expires_at,
                    "days_remaining": days_remaining,
                    "alert_sent": sent,
                    "alert_message": message,
                }
            )
        return results