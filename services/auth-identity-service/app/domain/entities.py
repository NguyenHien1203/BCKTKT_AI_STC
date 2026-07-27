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


@dataclass
class SystemConfig:
    """Cấu hình hệ thống chung (UC-06: Quản lý cấu hình hệ thống chung).

    Bản ghi "singleton" (luôn chỉ có 1 dòng, id=1): thời gian chờ (timeout)
    của request, dung lượng tải lên tối đa, ngôn ngữ mặc định. Sửa cấu hình
    được áp dụng ngay ("nạp lại nóng") vì mỗi request đọc thẳng từ CSDL,
    không cần khởi động lại service.
    """

    SUPPORTED_LANGUAGES = ("vi", "en")
    MIN_TIMEOUT_SECONDS = 1
    MAX_TIMEOUT_SECONDS = 600
    MIN_UPLOAD_SIZE_MB = 1
    MAX_UPLOAD_SIZE_MB = 1024

    id: Optional[int]
    request_timeout_seconds: int = 30
    max_upload_size_mb: int = 50
    default_language: str = "vi"
    updated_at: Optional[str] = None

    def update(
        self,
        request_timeout_seconds: int,
        max_upload_size_mb: int,
        default_language: str,
        updated_at: str,
    ) -> None:
        if not (
            self.MIN_TIMEOUT_SECONDS <= request_timeout_seconds <= self.MAX_TIMEOUT_SECONDS
        ):
            raise ValueError(
                f"Thời gian chờ phải trong khoảng {self.MIN_TIMEOUT_SECONDS}-"
                f"{self.MAX_TIMEOUT_SECONDS} giây"
            )
        if not (
            self.MIN_UPLOAD_SIZE_MB <= max_upload_size_mb <= self.MAX_UPLOAD_SIZE_MB
        ):
            raise ValueError(
                f"Dung lượng tải lên tối đa phải trong khoảng {self.MIN_UPLOAD_SIZE_MB}-"
                f"{self.MAX_UPLOAD_SIZE_MB} MB"
            )
        if default_language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Ngôn ngữ mặc định '{default_language}' không được hỗ trợ"
            )
        self.request_timeout_seconds = request_timeout_seconds
        self.max_upload_size_mb = max_upload_size_mb
        self.default_language = default_language
        self.updated_at = updated_at


@dataclass
class IntegrationEndpoint:
    """Cấu hình điểm cuối tích hợp hệ thống ngoài (UC-07: Quản lý cấu hình tích hợp).

    Mỗi dòng tương ứng 1 loại điểm cuối (`endpoint_type`): "KEYCLOAK" (IdP) hoặc
    "LGSP" (nền tảng tích hợp chia sẻ dữ liệu quốc gia/tỉnh). `extra_config` lưu
    các trường đặc thù theo loại (vd Keycloak: realm, client_id; LGSP: protocol).
    Sau khi lưu, hệ thống kiểm tra kết nối/giao thức và ghi nhận kết quả vào
    `is_connected` + `last_checked_at` — không chặn việc lưu cấu hình dù kiểm
    tra kết nối thất bại (để admin có thể sửa lại và kiểm tra lại).
    """

    ENDPOINT_TYPES = ("KEYCLOAK", "LGSP")

    id: Optional[int]
    endpoint_type: str
    base_url: str
    extra_config: dict
    is_connected: bool = False
    last_checked_at: Optional[str] = None
    last_check_message: str = ""

    def configure(self, base_url: str, extra_config: dict) -> None:
        if self.endpoint_type not in self.ENDPOINT_TYPES:
            raise ValueError(f"Loại điểm cuối '{self.endpoint_type}' không hợp lệ")
        if not base_url or not base_url.strip():
            raise ValueError("URL điểm cuối không được để trống")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ValueError("URL điểm cuối phải bắt đầu bằng http:// hoặc https://")
        self.base_url = base_url.strip()
        self.extra_config = dict(extra_config or {})
        # Đổi cấu hình -> trạng thái kiểm tra cũ không còn đáng tin, chờ kiểm tra lại.
        self.is_connected = False
        self.last_checked_at = None
        self.last_check_message = ""

    def record_check_result(self, is_connected: bool, message: str, checked_at: str) -> None:
        self.is_connected = is_connected
        self.last_check_message = message
        self.last_checked_at = checked_at