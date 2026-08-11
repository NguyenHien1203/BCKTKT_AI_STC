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


# ---------- UC-050: Sinh + kết xuất báo cáo ----------


class ReportGenerationFilterInput(BaseModel):
    """Bộ lọc dùng để sinh báo cáo — nếu để trống toàn bộ, hệ thống dùng
    lại cấu hình bộ lọc đã lưu ở UC-049 bước 3."""

    year: Optional[int] = Field(None, ge=1900, le=2100)
    period_type: Optional[str] = Field(None, pattern=_PERIOD_TYPE_PATTERN)
    period_value: Optional[int] = Field(None, ge=1, le=12)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class GeneratedReportFiltersResponse(BaseModel):
    year: int
    period_type: str
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None

    model_config = {"from_attributes": True}


class GeneratedReportResponse(BaseModel):
    """Bước 1 — "Sinh báo cáo theo mẫu + bộ lọc": hệ thống truy vấn Lớp
    ngữ nghĩa + kết xuất (xem trước dạng JSON trước khi kết xuất PDF/Excel)."""

    template: ReportTemplateResponse
    filters: GeneratedReportFiltersResponse
    columns: List[ReportTemplateColumn]
    rows: List[dict]
    row_count: int


class GeneratedReportLogResponse(BaseModel):
    id: int
    template_id: int
    user_id: int
    format: str
    year: int
    period_type: str
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    row_count: int
    generated_at: Optional[datetime] = None

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

# ---------- UC-051: Cấu hình báo cáo theo lịch ----------

_FREQUENCY_PATTERN = "^(DAILY|WEEKLY|MONTHLY)$"
_SCHEDULE_FORMAT_PATTERN = "^(PDF|EXCEL)$"


class ReportScheduleCreate(BaseModel):
    """Bước 1 — "Cấu hình lịch (hàng ngày/hàng tuần/hàng tháng)"."""

    user_id: int = Field(..., gt=0)
    frequency: str = Field(..., pattern=_FREQUENCY_PATTERN)
    time_of_day: str = Field(..., min_length=5, max_length=5, description="Định dạng 'HH:MM'")
    format: str = Field("PDF", pattern=_SCHEDULE_FORMAT_PATTERN)
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0=Thứ Hai .. 6=Chủ Nhật")
    day_of_month: Optional[int] = Field(None, ge=1, le=28)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    period_type: Optional[str] = Field(None, pattern=_PERIOD_TYPE_PATTERN)
    period_value: Optional[int] = Field(None, ge=1, le=12)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class ReportScheduleUpdate(BaseModel):
    """Sửa cấu hình lịch đã có."""

    frequency: str = Field(..., pattern=_FREQUENCY_PATTERN)
    time_of_day: str = Field(..., min_length=5, max_length=5)
    format: str = Field("PDF", pattern=_SCHEDULE_FORMAT_PATTERN)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=28)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    period_type: Optional[str] = Field(None, pattern=_PERIOD_TYPE_PATTERN)
    period_value: Optional[int] = Field(None, ge=1, le=12)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class ReportScheduleResponse(BaseModel):
    id: int
    template_id: int
    user_id: int
    frequency: str
    time_of_day: str
    format: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    year: Optional[int] = None
    period_type: Optional[str] = None
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportScheduleRecipientCreate(BaseModel):
    """Bước 2 — "Cấu hình người nhận (email)"."""

    email: str = Field(..., min_length=3, max_length=255)


class ReportScheduleRecipientResponse(BaseModel):
    id: int
    schedule_id: int
    email: str
    added_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportScheduleRunLogResponse(BaseModel):
    """Bước 3 — nhật ký mỗi lần "Tác vụ định kỳ (cron)" tự động sinh +
    gửi email báo cáo theo lịch."""

    id: int
    schedule_id: int
    status: str
    recipients_count: int
    row_count: int
    message: str
    run_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# ---------- UC-052: Đăng ký nhận cảnh báo dashboard ----------

_ALERT_OPERATOR_PATTERN = r"^(>|>=|<|<=)$"
_ALERT_CHANNEL_TYPE_PATTERN = "^(EMAIL|SLACK|WEBHOOK)$"
_ALERT_LOG_STATUS_PATTERN = "^(SENT|FAILED)$"


class DashboardAlertRuleCreate(BaseModel):
    """Bước 1 — "Cấu hình ngưỡng cảnh báo trên KPI"."""

    kpi_code: str = Field(..., min_length=1, max_length=50)
    user_id: int = Field(..., gt=0)
    operator: str = Field(..., pattern=_ALERT_OPERATOR_PATTERN, description="'>', '>=', '<' hoặc '<='")
    threshold_value: float = Field(...)
    year: int = Field(..., ge=1900, le=2100)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class DashboardAlertRuleUpdate(BaseModel):
    """Sửa cấu hình ngưỡng đã có."""

    operator: str = Field(..., pattern=_ALERT_OPERATOR_PATTERN)
    threshold_value: float = Field(...)
    year: int = Field(..., ge=1900, le=2100)
    org_unit_code: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=30)


class DashboardAlertRuleResponse(BaseModel):
    id: int
    dashboard_id: int
    kpi_code: str
    user_id: int
    operator: str
    threshold_value: float
    year: int
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardAlertChannelCreate(BaseModel):
    """Bước 2 — "Chọn kênh nhận (email / Slack / Webhook)"."""

    channel_type: str = Field(..., pattern=_ALERT_CHANNEL_TYPE_PATTERN)
    destination: str = Field(..., min_length=3, max_length=500)


class DashboardAlertChannelResponse(BaseModel):
    id: int
    alert_rule_id: int
    channel_type: str
    destination: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardAlertLogResponse(BaseModel):
    """Bước 3 — nhật ký mỗi lần hệ thống gửi cảnh báo do vượt ngưỡng."""

    id: int
    alert_rule_id: int
    channel_id: int
    channel_type: str
    kpi_value: Optional[float] = None
    threshold_value: float
    operator: str
    status: str
    message: str = ""
    triggered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardAlertEvaluationResponse(BaseModel):
    """Kết quả 1 lượt đánh giá ngưỡng (bước 3, "chạy thử ngay" hoặc do
    tác vụ định kỳ gọi)."""

    rule_id: int
    evaluated: bool
    triggered: bool
    kpi_value: Optional[float] = None
    reason: str
    logs: List[DashboardAlertLogResponse] = []