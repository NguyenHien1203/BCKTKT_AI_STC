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