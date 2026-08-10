from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ---------- UC-047: Xem Bảng điều khiển điều hành ----------

_CATEGORY_PATTERN = "^(NGAN_SACH|TAI_SAN_CONG|DAU_TU_CONG|GIA|TONG_HOP)$"


class DashboardCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2000)
    category: str = Field(..., pattern=_CATEGORY_PATTERN)
    superset_dashboard_uid: str = Field(..., min_length=1, max_length=255)
    embed_url: str = Field(..., min_length=1, max_length=1000)


class DashboardResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    category: str
    superset_dashboard_uid: str
    embed_url: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardFavoriteCreate(BaseModel):
    user_id: int = Field(..., gt=0)


class DashboardFavoriteResponse(BaseModel):
    id: int
    user_id: int
    dashboard_id: int
    pinned_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    code: str
    message: str


# ---------- UC-047 (nâng cấp): Superset Embedded Dashboard SDK + Guest Token ----------


class GuestTokenResponse(BaseModel):
    guest_token: str
    superset_dashboard_uid: str
    superset_domain: str = Field(
        ..., description="Domain Superset mà trình duyệt gọi thẳng (SUPERSET_PUBLIC_URL)."
    )