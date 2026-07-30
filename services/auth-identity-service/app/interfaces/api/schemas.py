from typing import Optional

from pydantic import BaseModel, Field


class OrgUnitCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    unit_type: str = Field(..., pattern="^(SO|PHONG|XA)$")
    parent_id: Optional[int] = None


class OrgUnitRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgUnitResponse(BaseModel):
    id: int
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int]
    is_active: bool

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    code: str
    message: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    org_unit_id: int
    role: str = Field("STAFF", pattern="^(ADMIN|STAFF|VIEWER)$")
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdateProfile(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)


class UserReassignOrgUnit(BaseModel):
    org_unit_id: int


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    org_unit_id: int
    role: str
    external_id: str
    is_active: bool
    is_locked: bool

    model_config = {"from_attributes": True}


class ReassignOrgUnitWithHistory(BaseModel):
    org_unit_id: int


class OrgUnitHistoryResponse(BaseModel):
    id: int
    user_id: int
    old_org_unit_id: Optional[int]
    new_org_unit_id: int
    changed_at: str

    model_config = {"from_attributes": True}


class ManualSyncResponse(BaseModel):
    remote_total: int
    matched: int
    unmatched_usernames: list[str]
    synced_at: str


class ForceLogoutResponse(BaseModel):
    revoked_sessions: int


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class CurrentUserResponse(UserResponse):
    pass


# ---------- UC-12 (Keycloak SSO): Authorization Code Flow + PKCE ----------


class OidcConfigResponse(BaseModel):
    enabled: bool
    auth_base_url: Optional[str] = None
    realm: Optional[str] = None
    client_id: Optional[str] = None
    # UC-13: khi enabled=true, app KHÔNG tự đổi/cấp lại mật khẩu nữa — trỏ
    # người dùng sang Keycloak Account Console (đã có sẵn màn hình đổi mật
    # khẩu, chính sách mật khẩu, MFA...). Tránh phải cấp cho backend quyền
    # Keycloak Admin API chỉ để làm lại việc Keycloak đã làm sẵn.
    account_console_url: Optional[str] = None


class OidcSessionRequest(BaseModel):
    access_token: str = Field(..., min_length=1)


class OidcSessionResponse(BaseModel):
    token: str
    user: UserResponse


# ---------- UC-13: Đổi mật khẩu / Cấp lại mật khẩu ----------


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=255)


class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=255)


class MessageResponse(BaseModel):
    message: str


# ---------- UC-05: Quản lý vai trò người dùng ----------


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    permissions: list[str] = Field(default_factory=list)


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    permissions: list[str]
    version: int

    model_config = {"from_attributes": True}


# ---------- UC-04: Quản lý quyền người dùng ----------


class AssignRoleRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=50)


class ConfigureDomainsRequest(BaseModel):
    permitted_domains: list[str] = Field(default_factory=list)
    permitted_unit_id: Optional[int] = None


# ---------- UC-06: Quản lý cấu hình hệ thống chung ----------


class SystemConfigUpdate(BaseModel):
    request_timeout_seconds: int = Field(..., ge=1, le=600)
    max_upload_size_mb: int = Field(..., ge=1, le=1024)
    default_language: str = Field(..., min_length=2, max_length=10)


class SystemConfigResponse(BaseModel):
    id: int
    request_timeout_seconds: int
    max_upload_size_mb: int
    default_language: str
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- UC-07: Quản lý cấu hình tích hợp ----------


class KeycloakConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    realm: str = Field(default="", max_length=100)
    client_id: str = Field(default="", max_length=100)


class LgspConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    protocol: str = Field(default="", max_length=50)


class IntegrationEndpointResponse(BaseModel):
    id: int
    endpoint_type: str
    base_url: str
    extra_config: dict
    is_connected: bool
    last_checked_at: Optional[str] = None
    last_check_message: str = ""

    model_config = {"from_attributes": True}


# ---------- UC-08: Quản lý cấu hình kênh thông báo ----------


class SmtpConfigUpdate(BaseModel):
    smtp_host: str = Field(..., min_length=1, max_length=255)
    smtp_port: int = Field(..., ge=1, le=65535)
    from_email: str = Field(..., min_length=3, max_length=255)
    username: str = Field(default="", max_length=255)
    password: str = Field(default="", max_length=255)
    test_recipient: str = Field(default="", max_length=255)


class SmsConfigUpdate(BaseModel):
    gateway_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=255)
    test_recipient: str = Field(..., min_length=1, max_length=30)


class WebhookConfigUpdate(BaseModel):
    webhook_url: str = Field(..., min_length=1, max_length=500)


class SendTestRequest(BaseModel):
    recipient: str = Field(default="", max_length=255)


class NotificationChannelResponse(BaseModel):
    id: int
    channel_type: str
    config: dict
    is_verified: bool
    last_test_at: Optional[str] = None
    last_test_message: str = ""

    model_config = {"from_attributes": True}


class ConfigureSensitivityRequest(BaseModel):
    sensitivity_level: str = Field(
        ..., pattern="^(PUBLIC|INTERNAL|CONFIDENTIAL|SECRET)$"
    )


# ---------- UC-09: Quản lý nhật ký truy cập và thao tác ----------


class AuditLogCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: str = Field(default="", max_length=100)
    detail: str = Field(default="", max_length=2000)
    ip_address: str = Field(default="", max_length=64)
    status: str = Field(default="SUCCESS", pattern="^(SUCCESS|FAILURE)$")


class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    resource_type: str
    resource_id: str
    detail: str
    ip_address: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}


# ---------- UC-10: Quản trị AI Audit Log ----------


class AiAuditLogCreate(BaseModel):
    trace_id: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)
    model: str = Field(default="", max_length=100)
    prompt: str = Field(..., min_length=1, max_length=10000)
    response: str = Field(default="", max_length=20000)
    sources: list[str] = Field(default_factory=list)
    permission_snapshot: dict = Field(default_factory=dict)
    prompt_version: str = Field(default="", max_length=50)


class AiAuditLogResponse(BaseModel):
    id: int
    trace_id: str
    username: str
    model: str
    prompt: str
    response: str
    sources: list[str]
    permission_snapshot: dict
    prompt_version: str
    created_at: str

    model_config = {"from_attributes": True}


class PermissionContextResponse(BaseModel):
    id: int
    user_id: int
    role_code: str
    permitted_domains: list[str]
    permitted_unit_id: Optional[int]
    sensitivity_level: str

    model_config = {"from_attributes": True}

# ---------- UC-11: Quản trị tài liệu hướng dẫn sử dụng ----------


class GuideDocumentResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    file_name: str
    content_type: str
    file_size: int
    current_version: int
    uploaded_by: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class GuideDocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version: int
    file_name: str
    content_type: str
    file_size: int
    uploaded_by: str
    created_at: str

    model_config = {"from_attributes": True}


class GuideDocumentMetaUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)


# ---------- UC-14: Quản lý phiên đăng nhập ----------


class SessionResponse(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: str
    created_at: str
    is_revoked: bool
    token_preview: str

    model_config = {"from_attributes": True}