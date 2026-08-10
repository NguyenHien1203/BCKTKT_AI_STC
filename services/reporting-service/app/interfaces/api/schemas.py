from datetime import datetime
from typing import List, Optional

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


# ---------- UC-048: Áp bộ lọc + xem chi tiết Bảng điều khiển ----------


class DashboardKpiCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    unit_of_measure: str = Field("", max_length=50)
    higher_is_better: bool = True


class DashboardKpiResponse(BaseModel):
    id: int
    dashboard_id: int
    code: str
    name: str
    unit_of_measure: str
    higher_is_better: bool
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardFilterInput(BaseModel):
    """Bước 1 UC-048 — bộ lọc năm/đơn vị/lĩnh vực."""

    year: int = Field(..., ge=1900, le=2100)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class KpiValueItem(BaseModel):
    kpi_code: str
    kpi_name: str
    unit_of_measure: str
    value: Optional[float] = None


class ApplyFiltersResponse(BaseModel):
    dashboard_id: int
    filters: DashboardFilterInput
    kpi_values: List[KpiValueItem]


class KpiBreakdownItem(BaseModel):
    label: str
    value: Optional[float] = None


class KpiDetailResponse(BaseModel):
    dashboard_id: int
    kpi_code: str
    kpi_name: str
    unit_of_measure: str
    filters: DashboardFilterInput
    value: Optional[float] = None
    breakdown: List[KpiBreakdownItem]


class KpiComparisonResponse(BaseModel):
    dashboard_id: int
    kpi_code: str
    kpi_name: str
    unit_of_measure: str
    filters: DashboardFilterInput
    current_year: int
    current_value: Optional[float] = None
    prior_year: int
    prior_value: Optional[float] = None
    delta: Optional[float] = None
    delta_percent: Optional[float] = None


class KpiExplanationRequest(BaseModel):
    requested_by: int = Field(..., gt=0)
    year: int = Field(..., ge=1900, le=2100)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


# ---------- UC-049: Chọn báo cáo theo mẫu + cấu hình bộ lọc ----------

_PERIOD_TYPE_PATTERN = "^(THANG|QUY|NAM)$"


class ReportTemplateColumn(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field("STRING", max_length=20)


class ReportTemplateCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2000)
    category: str = Field(..., pattern=_CATEGORY_PATTERN)
    columns: List[ReportTemplateColumn] = Field(..., min_length=1)
    available_periods: List[str] = Field(default_factory=lambda: ["NAM"])


class ReportTemplateResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    category: str
    columns: List[ReportTemplateColumn]
    available_periods: List[str]
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportTemplatePreviewResponse(BaseModel):
    """Bước 2 — "Chọn mẫu báo cáo": hệ thống hiển thị xem trước."""

    template: ReportTemplateResponse
    columns: List[ReportTemplateColumn]
    sample_rows: List[dict]


class ReportFilterConfigSave(BaseModel):
    """Bước 3 — "Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ)"."""

    user_id: int = Field(..., gt=0)
    year: int = Field(..., ge=1900, le=2100)
    period_type: str = Field(..., pattern=_PERIOD_TYPE_PATTERN)
    period_value: Optional[int] = Field(None, ge=1, le=12)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class ReportFilterConfigResponse(BaseModel):
    id: int
    template_id: int
    user_id: int
    year: int
    period_type: str
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    status: str
    saved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KpiExplanationResponse(BaseModel):
    id: int
    dashboard_id: int
    kpi_code: str
    year: int
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    requested_by: int
    explanation: str
    model: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}