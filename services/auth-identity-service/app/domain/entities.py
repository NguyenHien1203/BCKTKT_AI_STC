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


@dataclass
class User:
    """Người dùng hệ thống.

    Tương ứng UC-02: Quản lý người dùng (CRUD) (nhóm I. Quản trị hệ thống).
    Việc đồng bộ với Keycloak (nhà cung cấp danh tính) được trừu tượng hoá
    qua cổng `IdentityProviderClient` ở tầng infrastructure — xem SKILL.md mục D.
    """

    id: Optional[int]
    username: str
    full_name: str
    email: str
    org_unit_id: int
    role: str  # vd: "ADMIN" | "STAFF" | "VIEWER" (UC-05 sẽ mở rộng quản lý vai trò)
    is_active: bool = True

    def rename(self, full_name: str) -> None:
        if not full_name or not full_name.strip():
            raise ValueError("Họ tên không được để trống")
        self.full_name = full_name.strip()

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
