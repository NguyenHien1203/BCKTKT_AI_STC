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


class ConfigureSensitivityRequest(BaseModel):
    sensitivity_level: str = Field(
        ..., pattern="^(PUBLIC|INTERNAL|CONFIDENTIAL|SECRET)$"
    )


class PermissionContextResponse(BaseModel):
    id: int
    user_id: int
    role_code: str
    permitted_domains: list[str]
    permitted_unit_id: Optional[int]
    sensitivity_level: str

    model_config = {"from_attributes": True}