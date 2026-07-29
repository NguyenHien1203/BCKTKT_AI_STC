"""Domain entities cho ingestion-service."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DataSource:
    """Nguồn dữ liệu được đăng ký để tiếp nhận/đồng bộ (UC-015).

    `source_system` chỉ được là 1 trong 5 hệ thống nguồn theo BCKTKT:
    TABMIS, QLVBDH, MISA, QL_GIA, PMSTT. `code` là mã nguồn do Quản trị
    Tích hợp tự đặt, duy nhất toàn hệ thống.
    """

    SOURCE_SYSTEMS = ("TABMIS", "QLVBDH", "MISA", "QL_GIA", "PMSTT")
    SENSITIVITY_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET")

    id: Optional[int]
    code: str
    name: str
    source_system: str
    provider: str
    owner: str
    sensitivity_level: str = "INTERNAL"
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_source_system(self.source_system)
        self._validate_sensitivity_level(self.sensitivity_level)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã nguồn không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên nguồn không được để trống")

    @classmethod
    def _validate_source_system(cls, source_system: str) -> None:
        if source_system not in cls.SOURCE_SYSTEMS:
            raise ValueError(
                f"Hệ thống nguồn '{source_system}' không hợp lệ, "
                f"phải là 1 trong {cls.SOURCE_SYSTEMS}"
            )

    @classmethod
    def _validate_sensitivity_level(cls, sensitivity_level: str) -> None:
        if sensitivity_level not in cls.SENSITIVITY_LEVELS:
            raise ValueError(f"Mức nhạy cảm '{sensitivity_level}' không hợp lệ")

    def update_info(self, provider: str, owner: str, sensitivity_level: str) -> None:
        """Sửa thông tin nguồn: nhà cung cấp, chủ sở hữu, mức nhạy cảm."""
        self._validate_sensitivity_level(sensitivity_level)
        if not provider or not provider.strip():
            raise ValueError("Nhà cung cấp không được để trống")
        if not owner or not owner.strip():
            raise ValueError("Chủ sở hữu không được để trống")
        self.provider = provider.strip()
        self.owner = owner.strip()
        self.sensitivity_level = sensitivity_level

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Connector:
    """Bộ kết nối (plugin) trong thư viện bộ kết nối (UC-016).

    `connector_type` chỉ được là 1 trong 4 loại theo BCKTKT: FILE
    (tệp), REST_API, JDBC, SOAP. `entry_point` là đường dẫn mô-đun
    plugin (định dạng `package.module:ClassName`) — dùng để mô
    phỏng bước "hệ thống nạp mô-đun + kiểm tra giao diện" khi đăng
    ký bộ kết nối mới.
    """

    CONNECTOR_TYPES = ("FILE", "REST_API", "JDBC", "SOAP")
    INTERFACE_STATUSES = ("PASSED", "FAILED")

    id: Optional[int]
    code: str
    name: str
    connector_type: str
    version: str
    entry_point: str
    description: str = ""
    interface_status: str = "PASSED"
    is_active: bool = True
    restart_count: int = 0

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_connector_type(self.connector_type)
        self._validate_version(self.version)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã bộ kết nối không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên bộ kết nối không được để trống")

    @classmethod
    def _validate_connector_type(cls, connector_type: str) -> None:
        if connector_type not in cls.CONNECTOR_TYPES:
            raise ValueError(
                f"Loại bộ kết nối '{connector_type}' không hợp lệ, "
                f"phải là 1 trong {cls.CONNECTOR_TYPES}"
            )

    @staticmethod
    def _validate_version(version: str) -> None:
        if not version or not version.strip():
            raise ValueError("Phiên bản không được để trống")

    @staticmethod
    def check_interface(entry_point: str) -> bool:
        """Mô phỏng bước "nạp mô-đun + kiểm tra giao diện" khi đăng ký plugin.

        Giao diện hợp lệ khi `entry_point` theo định dạng
        `package.module:ClassName` (có dấu `.` phân tách module và
        dấu `:` phân tách tên lớp triển khai interface bộ kết nối).
        """
        if not entry_point or ":" not in entry_point:
            return False
        module_path, _, class_name = entry_point.partition(":")
        return bool(module_path.strip()) and "." in module_path and bool(class_name.strip())

    def update_version(self, new_version: str) -> None:
        """Cập nhật phiên bản bộ kết nối + tăng bộ đếm khởi động lại
        luân phiên tiến trình nhận sự kiện (rolling restart)."""
        self._validate_version(new_version)
        self.version = new_version.strip()
        self.restart_count += 1

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class SourceConnection:
    """Cấu hình kết nối tới nguồn dữ liệu (UC-017): API / DB / File.

    `config` chỉ chứa thông tin KHÔNG nhạy cảm (host, port, base_url,
    database, path...). Thông tin xác thực (username/password/api_key/
    token...) được mã hoá và lưu riêng ở `encrypted_credentials` (chuỗi
    đã mã hoá qua cổng `CredentialCrypto`) — domain layer không bao giờ
    giữ bản rõ (plaintext) sau khi mã hoá xong.
    """

    CONNECTION_TYPES = ("API", "DB", "FILE")
    TEST_STATUSES = ("UNTESTED", "SUCCESS", "FAILED")

    id: Optional[int]
    data_source_id: int
    connection_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    encrypted_credentials: str = ""
    last_test_status: str = "UNTESTED"
    last_test_message: str = ""
    last_tested_at: Optional[str] = None
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_data_source_id(self.data_source_id)
        self._validate_connection_type(self.connection_type)

    @staticmethod
    def _validate_data_source_id(data_source_id: int) -> None:
        if not data_source_id or data_source_id <= 0:
            raise ValueError("Phải chỉ định nguồn dữ liệu (data_source_id) hợp lệ")

    @classmethod
    def _validate_connection_type(cls, connection_type: str) -> None:
        if connection_type not in cls.CONNECTION_TYPES:
            raise ValueError(
                f"Loại kết nối '{connection_type}' không hợp lệ, "
                f"phải là 1 trong {cls.CONNECTION_TYPES}"
            )

    def record_test_result(self, success: bool, message: str, tested_at: str) -> None:
        """Ghi nhận kết quả sau khi hệ thống gọi thử kết nối."""
        self.last_test_status = "SUCCESS" if success else "FAILED"
        self.last_test_message = message
        self.last_tested_at = tested_at

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class CredentialAsset:
    """Certificate / API key gắn với 1 cấu hình kết nối (UC-017).

    Lưu lịch luân chuyển (`rotation_history`) mỗi lần certificate/API key
    được thay mới, phục vụ truy vết + làm căn cứ cảnh báo trước khi hết
    hạn (`expires_at`).
    """

    ASSET_TYPES = ("CERTIFICATE", "API_KEY")

    id: Optional[int]
    connection_id: int
    asset_type: str
    encrypted_value: str
    issued_at: str
    expires_at: str
    rotation_period_days: int = 90
    rotated_at: Optional[str] = None
    rotation_count: int = 0
    rotation_history: List[Dict[str, str]] = field(default_factory=list)
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_connection_id(self.connection_id)
        self._validate_asset_type(self.asset_type)
        self._validate_expires_at(self.expires_at)

    @staticmethod
    def _validate_connection_id(connection_id: int) -> None:
        if not connection_id or connection_id <= 0:
            raise ValueError("Phải chỉ định cấu hình kết nối (connection_id) hợp lệ")

    @classmethod
    def _validate_asset_type(cls, asset_type: str) -> None:
        if asset_type not in cls.ASSET_TYPES:
            raise ValueError(
                f"Loại tài sản xác thực '{asset_type}' không hợp lệ, "
                f"phải là 1 trong {cls.ASSET_TYPES}"
            )

    @staticmethod
    def _validate_expires_at(expires_at: str) -> None:
        if not expires_at:
            raise ValueError("Ngày hết hạn (expires_at) không được để trống")
        try:
            datetime.fromisoformat(expires_at)
        except ValueError as exc:
            raise ValueError(
                "Ngày hết hạn (expires_at) phải theo định dạng ISO-8601"
            ) from exc

    def rotate(self, new_encrypted_value: str, new_expires_at: str, rotated_at: str) -> None:
        """Luân chuyển (rotate) certificate/API key: lưu bản cũ vào lịch sử
        luân chuyển rồi thay bằng bản mới."""
        self._validate_expires_at(new_expires_at)
        self.rotation_history.append(
            {"rotated_at": rotated_at, "previous_expires_at": self.expires_at}
        )
        self.encrypted_value = new_encrypted_value
        self.expires_at = new_expires_at
        self.rotated_at = rotated_at
        self.rotation_count += 1

    def days_until_expiry(self, now: datetime) -> int:
        """Số ngày còn lại tới khi hết hạn (âm nếu đã hết hạn)."""
        expires = datetime.fromisoformat(self.expires_at)
        if expires.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif expires.tzinfo is not None and now.tzinfo is None:
            expires = expires.replace(tzinfo=None)
        return (expires - now).days

    def is_expiring_within(self, days_ahead: int, now: datetime) -> bool:
        """True nếu còn hoạt động và sẽ hết hạn trong vòng `days_ahead` ngày tới."""
        return self.is_active and self.days_until_expiry(now) <= days_ahead

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True