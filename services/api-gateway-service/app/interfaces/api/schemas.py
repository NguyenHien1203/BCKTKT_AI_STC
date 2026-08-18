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
    service_tier_code: Optional[str] = Field(
        default=None,
        description=(
            "UC-064: mã gói dịch vụ (FREE/STANDARD/PREMIUM, UC-060) áp giới hạn "
            "tần suất khi gọi Data API. Bỏ trống -> mặc định dùng gói FREE."
        ),
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
    service_tier_code: Optional[str] = None

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

# ---------------------------------------------------------------------------
# UC-064 — Cung cấp Data API cho IOC.
# ---------------------------------------------------------------------------


class DataApiQueryRequest(BaseModel):
    """Bước 1 — IOC gọi Data API tổng hợp. Khoá API truyền qua header
    `X-API-Key` (KHÔNG nằm trong body)."""

    dataset_code: str = Field(..., min_length=1, max_length=100)
    filters: Dict[str, Any] = Field(default_factory=dict)


class DataApiQueryResponse(BaseModel):
    dataset_code: str
    row_count: int
    rows: List[Dict[str, Any]]


class AuditLogResponse(BaseModel):
    """Bước 3 — 1 dòng nhật ký trong `audit.audit_log`."""

    id: int
    api_type: str
    endpoint_path: str
    consumer_code: str
    status: str
    api_key_id: Optional[int] = None
    reason: str = ""
    request_params: str = ""
    row_count: Optional[int] = None
    consumer_ip: Optional[str] = None
    called_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ.
# ---------------------------------------------------------------------------
class SearchApiQueryRequest(BaseModel):
    """Bước 1 — QLVBĐH gọi Search API. Khoá API truyền qua header
    `X-API-Key` (KHÔNG nằm trong body). `user_don_vi_code`/
    `user_security_level` là PHẠM VI CỦA NGƯỜI DÙNG CUỐI mà QLVBĐH gọi
    thay (khác phạm vi/scope của bản thân khoá API) — dùng ở bước "Hệ
    thống lọc theo phạm vi của người dùng đến từ QLVBĐH"."""

    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    user_don_vi_code: Optional[str] = Field(default=None, max_length=200)
    user_security_level: str = Field(default="PUBLIC", max_length=20)


class SearchResultSourceResponse(BaseModel):
    """Dẫn nguồn của 1 kết quả tìm kiếm."""

    source_system: str
    doc_code: str
    source_url: str


class SearchResultItemResponse(BaseModel):
    doc_code: str
    title: str
    snippet: str
    score: float
    vector_score: float
    bm25_score: float
    don_vi_code: Optional[str] = None
    security_level: str
    source: SearchResultSourceResponse


class SearchApiQueryResponse(BaseModel):
    query: str
    result_count: int
    results: List[SearchResultItemResponse]


# ---------------------------------------------------------------------------
# UC-065 — Cung cấp API qua LGSP.
# ---------------------------------------------------------------------------
class LgspRequestPayload(BaseModel):
    """Bước 1 — Cổng LGSP chuyển tiếp yêu cầu. Chứng thư mTLS truyền qua
    header `X-Client-Cert-Serial` (KHÔNG nằm trong body)."""

    request_id: str = Field(..., min_length=1, max_length=100, description="Mã giao dịch do Cổng LGSP sinh")
    service_code: str = Field(..., min_length=1, max_length=100, description="Mã dịch vụ/bộ dữ liệu cần lấy")
    payload: Dict[str, Any] = Field(default_factory=dict)


class LgspResponseEnvelope(BaseModel):
    """Bước 3 — Phong bì phản hồi theo chuẩn LGSP, LUÔN trả về (thành
    công lẫn bị từ chối/lỗi) — không dùng mã lỗi HTTP rời rạc."""

    request_id: str
    response_code: str
    response_message: str
    processed_at: datetime
    data: Optional[Dict[str, Any]] = None