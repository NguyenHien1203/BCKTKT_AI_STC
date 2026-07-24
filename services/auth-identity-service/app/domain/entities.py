"""Domain entities — thuần Python, không phụ thuộc framework/ORM."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class OrgUnit:
    """Đơn vị trong cơ cấu tổ chức (Sở / Phòng / Xã...).

    Tương ứng UC-01: Quản lý cơ cấu tổ chức (nhóm I. Quản trị hệ thống).
    """

    id: Optional[int]
    code: str
    name: str
    unit_type: str  # "SO" | "PHONG" | "XA" ...
    parent_id: Optional[int] = None
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("Tên đơn vị không được để trống")
        self.name = new_name.strip()
