"""Pydantic schemas cho UC-058 — Quản lý danh mục API."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApiCatalogEntryCreate(BaseModel):
    """Bước 1 — Publish API mới."""

    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    api_type: str = Field(..., description="SEARCH | QA | DATA | METADATA")
    endpoint_path: str = Field(..., min_length=1, max_length=500)
    version: str = Field(..., min_length=1, max_length=50)
    sunset_date: Optional[date] = None


class ApiCatalogVersionConfigure(BaseModel):
    """Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ."""

    version: str = Field(..., min_length=1, max_length=50)
    sunset_date: Optional[date] = None
    change_note: str = ""


class ApiCatalogEntryResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    api_type: str
    endpoint_path: str
    version: str
    status: str
    version_no: int
    sunset_date: Optional[date] = None
    published_at: Optional[datetime] = None
    unpublished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiCatalogVersionHistoryResponse(BaseModel):
    id: int
    entry_id: int
    version_no: int
    version: str
    sunset_date: Optional[date] = None
    change_note: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    code: str
    message: str


# ---------------------------------------------------------------------------
# UC-059 — Quản lý API key.
# ---------------------------------------------------------------------------


class ApiKeyCreate(BaseModel):
    """Bước 1 — Tạo khoá API cho đơn vị khai thác."""

    consumer_name: str = Field(..., min_length=1, max_length=255)
    consumer_code: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    scope: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Phạm vi truy cập, danh sách phân tách bởi dấu phẩy, vd 'SEARCH,QA'",
    )


class ApiKeyResponse(BaseModel):
    """Response CHUẨN — KHÔNG chứa raw key/hash, chỉ `key_prefix` để định danh."""

    id: int
    consumer_name: str
    consumer_code: str
    description: str
    scope: str
    key_prefix: str
    status: str
    created_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    rotated_at: Optional[datetime] = None
    grace_expires_at: Optional[datetime] = None
    previous_key_id: Optional[int] = None
    rotated_to_id: Optional[int] = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response DUY NHẤT có kèm `raw_key` — chỉ trả về lúc tạo/luân chuyển."""

    raw_key: str = Field(
        ..., description="Giá trị khoá API thật — chỉ hiển thị 1 LẦN DUY NHẤT."
    )


class ApiKeyRotateRequest(BaseModel):
    """Bước 3 — Luân chuyển khoá API (tự động / thủ công)."""

    grace_period_days: Optional[int] = Field(
        default=None, ge=0, le=365, description="Số ngày ân hạn cho khoá cũ"
    )
    rotation_mode: str = Field(
        default="MANUAL", description="MANUAL (thủ công) | AUTO (tự động)"
    )


class ApiKeyRotateResponse(BaseModel):
    old_key: ApiKeyResponse
    new_key: ApiKeyCreatedResponse


class ApiKeyUsageLogCreate(BaseModel):
    """Bước 4 — Ghi nhật ký sử dụng khoá API."""

    endpoint_path: str = Field(..., min_length=1, max_length=500)
    method: str = Field(default="GET", max_length=10)
    status_code: Optional[int] = None
    consumer_ip: Optional[str] = Field(default=None, max_length=64)
    note: str = ""


class ApiKeyUsageLogResponse(BaseModel):
    id: int
    api_key_id: int
    endpoint_path: str
    method: str
    status_code: Optional[int] = None
    consumer_ip: Optional[str] = None
    note: str
    called_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.
# ---------------------------------------------------------------------------


class ServiceTierCreate(BaseModel):
    """Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp)."""

    code: str = Field(..., description="FREE | STANDARD | PREMIUM")
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ServiceTierUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    is_active: Optional[bool] = None


class ServiceTierResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RateLimitPolicyConfigure(BaseModel):
    """Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày)."""

    requests_per_second: int = Field(..., gt=0, description="Giới hạn req/giây")
    requests_per_day: int = Field(..., gt=0, description="Giới hạn req/ngày")


class RateLimitPolicyResponse(BaseModel):
    id: int
    tier_id: int
    requests_per_second: int
    requests_per_day: int
    applied_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BurstPolicyConfigure(BaseModel):
    """Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết."""

    burst_limit: int = Field(..., gt=0, description="Số request đột biến tối đa")
    window_seconds: int = Field(..., gt=0, description="Cửa sổ thời gian đột biến (giây)")
    throttle_policy: str = Field(..., description="REJECT | QUEUE | DELAY")


class BurstPolicyResponse(BaseModel):
    id: int
    tier_id: int
    burst_limit: int
    window_seconds: int
    throttle_policy: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# UC-061 — Theo dõi mức sử dụng API + chỉ số.
# ---------------------------------------------------------------------------


class ApiUsageSummaryResponse(BaseModel):
    """Bước 1 — tổng quan hiện hành đọc từ Prometheus."""

    requests_per_second: float
    avg_latency_ms: float
    error_rate_percent: float
    total_requests: int


class ApiUsageSeriesPointResponse(BaseModel):
    timestamp: str
    requests_per_second: float
    avg_latency_ms: float
    error_rate_percent: float


class ApiUsageDashboardResponse(BaseModel):
    """Bước 1 — Xem bảng điều khiển mức sử dụng API."""

    window_minutes: int
    step_minutes: int
    summary: ApiUsageSummaryResponse
    series: List[ApiUsageSeriesPointResponse]


class ApiConsumerUsageResponse(BaseModel):
    """Bước 2 — Xem chi tiết theo đơn vị khai thác."""

    consumer_code: str
    requests_per_second: float
    avg_latency_ms: float
    error_rate_percent: float
    total_requests: int


class AlertmanagerWebhookPayload(BaseModel):
    """Bước 3 — cấu trúc payload webhook thật của Alertmanager
    (https://prometheus.io/docs/alerting/latest/configuration/#webhook_config).
    Chỉ khai báo các trường hệ thống thật sự dùng, cho phép các trường
    khác (`version`/`groupKey`/`groupLabels`/...) đi kèm mà không lỗi."""

    receiver: Optional[str] = None
    status: Optional[str] = None
    alerts: List[Dict[str, Any]] = Field(..., min_length=1)

    model_config = {"extra": "allow"}


class ApiAnomalyAlertResponse(BaseModel):
    id: int
    fingerprint: str
    alert_name: str
    severity: str
    status: str
    summary: str
    description: str
    consumer_code: Optional[str] = None
    endpoint_path: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác.
# ---------------------------------------------------------------------------


class MtlsCertificateRegister(BaseModel):
    """Bước 1 — Đăng ký chứng thư của đơn vị khai thác."""

    consumer_code: str = Field(..., min_length=1, max_length=100)
    consumer_name: str = Field(..., min_length=1, max_length=255)
    common_name: str = Field(..., min_length=1, max_length=255)
    serial_number: str = Field(..., min_length=1, max_length=128)
    pem_certificate: str = Field(..., min_length=1)
    not_before: datetime
    not_after: datetime


class MtlsCertificateResponse(BaseModel):
    id: int
    consumer_code: str
    consumer_name: str
    common_name: str
    serial_number: str
    fingerprint_sha256: str
    not_before: datetime
    not_after: datetime
    status: str
    registered_at: Optional[datetime] = None
    rotated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: str = ""
    previous_certificate_id: Optional[int] = None
    rotated_to_id: Optional[int] = None

    model_config = {"from_attributes": True}


class MtlsCertificateRotateRequest(BaseModel):
    """Bước 2 — Luân chuyển chứng thư (chứng thư mới thay thế)."""

    common_name: str = Field(..., min_length=1, max_length=255)
    serial_number: str = Field(..., min_length=1, max_length=128)
    pem_certificate: str = Field(..., min_length=1)
    not_before: datetime
    not_after: datetime


class MtlsCertificateRotateResponse(BaseModel):
    old_certificate: MtlsCertificateResponse
    new_certificate: MtlsCertificateResponse


class MtlsCertificateRevokeRequest(BaseModel):
    """Bước 3 — Thu hồi chứng thư."""

    reason: str = ""


class CertificateRevocationEntryResponse(BaseModel):
    """Bước 3 — 1 dòng trong CRL."""

    id: int
    certificate_id: int
    consumer_code: str
    serial_number: str
    fingerprint_sha256: str
    reason: str = ""
    revoked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CertificateRevocationCheckResponse(BaseModel):
    serial_number: str
    is_revoked: bool