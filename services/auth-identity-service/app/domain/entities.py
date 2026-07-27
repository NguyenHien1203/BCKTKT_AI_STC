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
    password_hash: str = ""
    external_id: str = ""  # id người dùng ở IdP (Keycloak) — rỗng nếu chưa đồng bộ
    is_active: bool = True
    is_locked: bool = False  # UC-03: khoá/mở khoá (khác is_active — xoá mềm của UC-02)

    def rename(self, full_name: str) -> None:
        if not full_name or not full_name.strip():
            raise ValueError("Họ tên không được để trống")
        self.full_name = full_name.strip()

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def lock(self) -> None:
        self.is_locked = True

    def unlock(self) -> None:
        self.is_locked = False

    def can_login(self) -> bool:
        return self.is_active and not self.is_locked


@dataclass
class UserSession:
    """Phiên đăng nhập (UC-12 Đăng nhập/Đăng xuất, UC-03 buộc đăng xuất)."""

    id: Optional[int]
    user_id: int
    token: str
    created_at: str
    is_revoked: bool = False

    def revoke(self) -> None:
        self.is_revoked = True


@dataclass
class OrgUnitAssignmentHistory:
    """Lịch sử chuyển đơn vị công tác của người dùng (UC-03)."""

    id: Optional[int]
    user_id: int
    old_org_unit_id: Optional[int]
    new_org_unit_id: int
    changed_at: str

@dataclass
class Role:
    """Vai trò người dùng (UC-05), gồm 1 bộ quyền (danh sách mã quyền).
 
    UC-04 (Quản lý quyền người dùng) sẽ dùng Role này để tính permission_context
    thực tế cho từng user, kết hợp thêm permitted_domains/unit/mức nhạy cảm.
    """
 
    id: Optional[int]
    code: str
    name: str
    description: str
    permissions: list  # list[str] mã quyền, vd ["USER_MANAGE", "REPORT_VIEW"]
    version: int = 1
 
    def update(self, name: str, description: str, permissions: list) -> None:
        if not name or not name.strip():
            raise ValueError("Tên vai trò không được để trống")
        self.name = name.strip()
        self.description = description.strip() if description else ""
        self.permissions = list(permissions)
        self.version += 1

 
@dataclass
class UserPermissionContext:
    """Ngữ cảnh quyền thực tế của người dùng (UC-04: Quản lý quyền người dùng).
 
    Đây là bản ghi "runtime" tổng hợp từ vai trò (UC-05 `Role`) cộng thêm phạm
    vi truy cập dữ liệu bổ sung mà UC-04 cho phép cấu hình riêng theo từng
    người dùng: các miền dữ liệu được phép (`permitted_domains`), đơn vị được
    phép truy cập (`permitted_unit_id`), và mức nhạy cảm dữ liệu tối đa được
    xem (`sensitivity_level`).
    """
 
    SENSITIVITY_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET")
 
    id: Optional[int]
    user_id: int
    role_code: str
    permitted_domains: list  # list[str], vd ["TAI_SAN", "NGAN_SACH", "GIA"]
    permitted_unit_id: Optional[int] = None
    sensitivity_level: str = "INTERNAL"
 
    def assign_role(self, role_code: str) -> None:
        if not role_code or not role_code.strip():
            raise ValueError("Mã vai trò không được để trống")
        self.role_code = role_code.strip()
 
    def configure_domains(self, permitted_domains: list, permitted_unit_id: Optional[int]) -> None:
        self.permitted_domains = list(permitted_domains or [])
        self.permitted_unit_id = permitted_unit_id
 
    def configure_sensitivity(self, sensitivity_level: str) -> None:
        if sensitivity_level not in self.SENSITIVITY_LEVELS:
            raise ValueError(f"Mức nhạy cảm '{sensitivity_level}' không hợp lệ")
        self.sensitivity_level = sensitivity_level
