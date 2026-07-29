"""Domain entities cho ingestion-service."""
from dataclasses import dataclass
from typing import Optional


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