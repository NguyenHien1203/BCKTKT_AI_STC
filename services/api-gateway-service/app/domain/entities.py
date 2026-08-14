"""Domain entities cho api-gateway-service.

UC-058 — Quản lý danh mục API:
  (1) Publish API mới (Search / QA / Data / Metadata) -> hệ thống cập nhật
      danh mục.
  (2) Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối.
  (3) Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống lưu.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class ApiCatalogEntry:
    """1 API trong danh mục API do `api-gateway-service` công bố.

    `api_type` xác định loại API theo đúng 4 nhóm nghiệp vụ của UC-058
    (Search/QA/Data/Metadata — tương ứng UC-066/067/064/068 sẽ implement
    sau). `status` PUBLISHED = đang công bố (điểm cuối đang hoạt động),
    UNPUBLISHED = đã gỡ công bố (điểm cuối bị vô hiệu hoá — bước 2).
    `version`/`sunset_date` (ngày ngừng hỗ trợ) được cấu hình ở bước 3,
    mỗi lần cấu hình lại tăng `version_no` (số thứ tự nội bộ, KHÁC
    `version` là chuỗi hiển thị dạng "v1"/"2024-01" do người quản trị đặt)
    và ghi 1 bản ghi lịch sử `ApiCatalogVersionHistory`.
    """

    API_TYPES = ("SEARCH", "QA", "DATA", "METADATA")
    STATUSES = ("PUBLISHED", "UNPUBLISHED")

    id: Optional[int]
    code: str
    name: str
    description: str
    api_type: str
    endpoint_path: str
    version: str
    status: str = "PUBLISHED"
    version_no: int = 1
    sunset_date: Optional[date] = None
    published_at: Optional[datetime] = None
    unpublished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_api_type(self.api_type)
        self._validate_endpoint_path(self.endpoint_path)
        self._validate_version(self.version)
        self._validate_status(self.status)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã API không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên API không được để trống")

    @classmethod
    def _validate_api_type(cls, api_type: str) -> None:
        if api_type not in cls.API_TYPES:
            raise ValueError(
                f"Loại API '{api_type}' không hợp lệ, phải thuộc {cls.API_TYPES}"
            )

    @staticmethod
    def _validate_endpoint_path(endpoint_path: str) -> None:
        if not endpoint_path or not endpoint_path.strip():
            raise ValueError("Đường dẫn điểm cuối (endpoint) không được để trống")
        if not endpoint_path.startswith("/"):
            raise ValueError("Đường dẫn điểm cuối phải bắt đầu bằng '/'")

    @staticmethod
    def _validate_version(version: str) -> None:
        if not version or not version.strip():
            raise ValueError("Phiên bản API không được để trống")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(
                f"Trạng thái '{status}' không hợp lệ, phải thuộc {cls.STATUSES}"
            )

    @property
    def is_published(self) -> bool:
        return self.status == "PUBLISHED"

    def unpublish(self, when: datetime) -> None:
        """Bước 2 — Gỡ công bố API: hệ thống vô hiệu hoá điểm cuối."""
        if self.status == "UNPUBLISHED":
            raise ValueError("API đã được gỡ công bố trước đó")
        self.status = "UNPUBLISHED"
        self.unpublished_at = when

    def republish(self, when: datetime) -> None:
        """Công bố lại API đã gỡ (đối xứng với `unpublish`, hỗ trợ sửa sai)."""
        if self.status == "PUBLISHED":
            raise ValueError("API đang được công bố, không cần công bố lại")
        self.status = "PUBLISHED"
        self.published_at = when
        self.unpublished_at = None

    def configure_version(
        self,
        version: str,
        sunset_date: Optional[date],
    ) -> None:
        """Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ."""
        self._validate_version(version)
        self.version = version
        self.sunset_date = sunset_date
        self.version_no += 1


@dataclass
class ApiCatalogVersionHistory:
    """Lịch sử phiên bản append-only của 1 API trong danh mục (bước 3)."""

    id: Optional[int]
    entry_id: int
    version_no: int
    version: str
    sunset_date: Optional[date]
    change_note: str = ""
    created_at: Optional[datetime] = None