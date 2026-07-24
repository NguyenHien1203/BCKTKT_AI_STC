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
