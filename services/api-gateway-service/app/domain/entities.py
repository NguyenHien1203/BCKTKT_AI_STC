"""Domain entities cho api-gateway-service.

UC-058 — Quản lý danh mục API:
  (1) Publish API mới (Search / QA / Data / Metadata) -> hệ thống cập nhật
      danh mục.
  (2) Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối.
  (3) Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống lưu.
"""
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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


# ---------------------------------------------------------------------------
# UC-059 — Quản lý API key.
#
# Flow:
#   (1) Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá + phạm vi.
#   (2) Thu hồi khoá API -> hệ thống thu hồi.
#   (3) Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo khoá mới
#       + thời gian ân hạn (grace period) cho khoá cũ.
#   (4) Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký.
# ---------------------------------------------------------------------------

KEY_PREFIX = "gw_"


@dataclass
class ApiKey:
    """1 khoá API cấp cho 1 đơn vị khai thác (consumer).

    Giá trị khoá thật (raw key) KHÔNG BAO GIỜ được lưu — chỉ lưu
    `key_hash` (SHA-256) để xác thực về sau, và `key_prefix` (đoạn đầu,
    không nhạy cảm) để định danh/hiển thị trong danh sách. Raw key chỉ
    được trả về 1 LẦN DUY NHẤT tại thời điểm tạo khoá (bước 1) hoặc luân
    chuyển khoá (bước 3, cho khoá MỚI) — không có cách nào lấy lại sau đó.

    `status`: ACTIVE = đang dùng được; REVOKED = đã bị thu hồi (bước 2,
    vĩnh viễn, không dùng được nữa); ROTATED = đã được luân chuyển sang
    khoá mới (bước 3) — vẫn còn hiệu lực đến hết `grace_expires_at` (thời
    gian ân hạn) để đơn vị khai thác kịp chuyển sang khoá mới, sau đó hết
    hiệu lực.
    """

    STATUSES = ("ACTIVE", "REVOKED", "ROTATED")
    DEFAULT_GRACE_PERIOD_DAYS = 7

    id: Optional[int]
    consumer_name: str
    consumer_code: str
    description: str
    scope: str
    key_prefix: str
    key_hash: str
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    rotated_at: Optional[datetime] = None
    grace_expires_at: Optional[datetime] = None
    previous_key_id: Optional[int] = None
    rotated_to_id: Optional[int] = None

    def __post_init__(self) -> None:
        self._validate_consumer_name(self.consumer_name)
        self._validate_consumer_code(self.consumer_code)
        self._validate_scope(self.scope)
        self._validate_status(self.status)

    @staticmethod
    def _validate_consumer_name(consumer_name: str) -> None:
        if not consumer_name or not consumer_name.strip():
            raise ValueError("Tên đơn vị khai thác không được để trống")

    @staticmethod
    def _validate_consumer_code(consumer_code: str) -> None:
        if not consumer_code or not consumer_code.strip():
            raise ValueError("Mã đơn vị khai thác không được để trống")

    @staticmethod
    def _validate_scope(scope: str) -> None:
        if not scope or not scope.strip():
            raise ValueError("Phạm vi (scope) của khoá API không được để trống")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(
                f"Trạng thái '{status}' không hợp lệ, phải thuộc {cls.STATUSES}"
            )

    @staticmethod
    def generate_raw_key() -> str:
        """Sinh khoá API ngẫu nhiên, an toàn (không lưu ở bất kỳ đâu)."""
        return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        consumer_name: str,
        consumer_code: str,
        description: str,
        scope: str,
        when: datetime,
        previous_key_id: Optional[int] = None,
    ) -> tuple["ApiKey", str]:
        """Bước 1 (hoặc khoá mới sinh ra ở bước 3) — sinh khoá + phạm vi.

        Trả về (entity, raw_key) — `raw_key` chỉ tồn tại trong bộ nhớ, gọi
        nơi nào cần trả cho người dùng đúng 1 lần rồi bỏ đi.
        """
        raw_key = cls.generate_raw_key()
        entry = cls(
            id=None,
            consumer_name=consumer_name,
            consumer_code=consumer_code,
            description=description,
            scope=scope,
            key_prefix=raw_key[: len(KEY_PREFIX) + 8],
            key_hash=cls.hash_key(raw_key),
            status="ACTIVE",
            created_at=when,
            previous_key_id=previous_key_id,
        )
        return entry, raw_key

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def is_valid_at(self, now: datetime) -> bool:
        """Khoá còn dùng được tại thời điểm `now` hay không.

        ACTIVE luôn hợp lệ; ROTATED chỉ còn hợp lệ trong thời gian ân hạn;
        REVOKED không bao giờ hợp lệ.
        """
        if self.status == "ACTIVE":
            return True
        if self.status == "ROTATED":
            return self.grace_expires_at is not None and now <= self.grace_expires_at
        return False

    def revoke(self, when: datetime) -> None:
        """Bước 2 — Thu hồi khoá API -> hệ thống thu hồi."""
        if self.status == "REVOKED":
            raise ValueError("Khoá API đã bị thu hồi trước đó")
        self.status = "REVOKED"
        self.revoked_at = when

    def mark_rotated(
        self,
        when: datetime,
        grace_period_days: int,
        new_key_id: int,
    ) -> None:
        """Bước 3 — đánh dấu khoá HIỆN TẠI đã được luân chuyển sang khoá
        mới (`new_key_id`), còn hiệu lực trong `grace_period_days` ngày ân
        hạn kể từ `when`."""
        if self.status != "ACTIVE":
            raise ValueError(
                "Chỉ có thể luân chuyển khoá API đang ở trạng thái ACTIVE"
            )
        if grace_period_days < 0:
            raise ValueError("Thời gian ân hạn không được là số âm")
        self.status = "ROTATED"
        self.rotated_at = when
        self.grace_expires_at = when + timedelta(days=grace_period_days)
        self.rotated_to_id = new_key_id


@dataclass
class ApiKeyUsageLog:
    """Bước 4 — Nhật ký sử dụng khoá API (append-only)."""

    id: Optional[int]
    api_key_id: int
    endpoint_path: str
    method: str = "GET"
    status_code: Optional[int] = None
    consumer_ip: Optional[str] = None
    note: str = ""
    called_at: Optional[datetime] = None