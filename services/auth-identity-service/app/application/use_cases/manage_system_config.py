"""Application layer — UC-06: Quản lý cấu hình hệ thống chung.

Đối chiếu docs/use_cases.json id=6: xem cấu hình chung (thời gian chờ, dung
lượng tải lên tối đa, ngôn ngữ mặc định) và sửa cấu hình — hệ thống lưu và áp
dụng ngay ("nạp lại nóng"). Vì service đọc cấu hình trực tiếp từ CSDL ở mỗi
lượt gọi `get_config`, không cần khởi động lại service để áp dụng thay đổi.
"""
from datetime import datetime, timezone

from app.domain.entities import SystemConfig
from app.domain.exceptions import InvalidSystemConfig
from app.domain.repositories import SystemConfigRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SystemConfigService:
    def __init__(self, config_repo: SystemConfigRepository):
        self._configs = config_repo

    def get_config(self) -> SystemConfig:
        """Xem cấu hình chung — tự khởi tạo giá trị mặc định lần đầu truy vấn."""
        config = self._configs.get()
        if config is None:
            config = SystemConfig(id=None, updated_at=_utc_now_iso())
            config = self._configs.save(config)
        return config

    def update_config(
        self,
        request_timeout_seconds: int,
        max_upload_size_mb: int,
        default_language: str,
    ) -> SystemConfig:
        """Sửa cấu hình — lưu và áp dụng ngay (nạp lại nóng)."""
        config = self.get_config()
        try:
            config.update(
                request_timeout_seconds=request_timeout_seconds,
                max_upload_size_mb=max_upload_size_mb,
                default_language=default_language,
                updated_at=_utc_now_iso(),
            )
        except ValueError as exc:
            raise InvalidSystemConfig(str(exc)) from exc
        return self._configs.save(config)