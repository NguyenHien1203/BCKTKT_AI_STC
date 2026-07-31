from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ---------- UC-015: Đăng ký và quản lý nguồn dữ liệu ----------

_SOURCE_SYSTEM_PATTERN = "^(TABMIS|QLVBDH|MISA|QL_GIA|PMSTT)$"
_SENSITIVITY_PATTERN = "^(PUBLIC|INTERNAL|CONFIDENTIAL|SECRET)$"


class DataSourceCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    source_system: str = Field(..., pattern=_SOURCE_SYSTEM_PATTERN)
    provider: str = Field(..., min_length=1, max_length=255)
    owner: str = Field(..., min_length=1, max_length=255)
    sensitivity_level: str = Field("INTERNAL", pattern=_SENSITIVITY_PATTERN)


class DataSourceUpdate(BaseModel):
    provider: str = Field(..., min_length=1, max_length=255)
    owner: str = Field(..., min_length=1, max_length=255)
    sensitivity_level: str = Field(..., pattern=_SENSITIVITY_PATTERN)


class DataSourceResponse(BaseModel):
    id: int
    code: str
    name: str
    source_system: str
    provider: str
    owner: str
    sensitivity_level: str
    is_active: bool

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    code: str
    message: str


# ---------- UC-016: Quản lý thư viện bộ kết nối ----------

_CONNECTOR_TYPE_PATTERN = "^(FILE|REST_API|JDBC|SOAP)$"


class ConnectorCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    connector_type: str = Field(..., pattern=_CONNECTOR_TYPE_PATTERN)
    version: str = Field(..., min_length=1, max_length=50)
    entry_point: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Đường dẫn mô-đun plugin, định dạng 'package.module:ClassName'",
    )
    description: str = Field("", max_length=500)


class ConnectorVersionUpdate(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)


class ConnectorResponse(BaseModel):
    id: int
    code: str
    name: str
    connector_type: str
    version: str
    entry_point: str
    description: str
    interface_status: str
    is_active: bool
    restart_count: int

    model_config = {"from_attributes": True}


# ---------- UC-017: Cấu hình kết nối nguồn (credentials/cert) ----------

_CONNECTION_TYPE_PATTERN = "^(API|DB|FILE)$"
_ASSET_TYPE_PATTERN = "^(CERTIFICATE|API_KEY)$"


class SourceConnectionCreate(BaseModel):
    data_source_id: int = Field(..., gt=0)
    connection_type: str = Field(..., pattern=_CONNECTION_TYPE_PATTERN)
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Thông tin KHÔNG nhạy cảm: host, port, base_url, database, path...",
    )
    credentials: Dict[str, Any] = Field(
        default_factory=dict,
        description="Thông tin xác thực (username/password/api_key/token...) sẽ được mã hoá trước khi lưu",
    )


class SourceConnectionUpdate(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Bỏ trống nếu không muốn đổi thông tin xác thực hiện có",
    )


class SourceConnectionResponse(BaseModel):
    """Không bao giờ trả về `encrypted_credentials` hay bản rõ thông tin xác thực."""

    id: int
    data_source_id: int
    connection_type: str
    config: Dict[str, Any]
    last_test_status: str
    last_test_message: str
    last_tested_at: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class CredentialAssetCreate(BaseModel):
    connection_id: int = Field(..., gt=0)
    asset_type: str = Field(..., pattern=_ASSET_TYPE_PATTERN)
    secret_value: str = Field(
        ..., min_length=1, description="Nội dung certificate (PEM) hoặc API key — sẽ được mã hoá"
    )
    expires_at: str = Field(..., description="Ngày hết hạn, định dạng ISO-8601")
    rotation_period_days: int = Field(90, gt=0)


class CredentialAssetRotate(BaseModel):
    secret_value: str = Field(..., min_length=1)
    expires_at: str = Field(..., description="Ngày hết hạn mới, định dạng ISO-8601")


class CredentialAssetResponse(BaseModel):
    """Không bao giờ trả về `encrypted_value` hay bản rõ certificate/API key."""

    id: int
    connection_id: int
    asset_type: str
    issued_at: str
    expires_at: str
    rotation_period_days: int
    rotated_at: Optional[str] = None
    rotation_count: int
    rotation_history: List[Dict[str, str]]
    is_active: bool

    model_config = {"from_attributes": True}


class ExpiryAlertResult(BaseModel):
    asset_id: int
    connection_id: int
    asset_type: str
    expires_at: str
    days_remaining: int
    alert_sent: bool
    alert_message: str

# ---------- UC-018: Định nghĩa tập dữ liệu của nguồn ----------

_DATA_TYPE_PATTERN = "^(STRING|INTEGER|BIGINT|DECIMAL|BOOLEAN|DATE|DATETIME|JSON)$"
_PARTITION_STRATEGY_PATTERN = "^(NONE|RANGE|LIST|HASH)$"


class SchemaFieldSchema(BaseModel):
    """1 trường trong lược đồ của tập dữ liệu."""

    name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field(..., pattern=_DATA_TYPE_PATTERN)
    nullable: bool = Field(True)
    description: str = Field("", max_length=500)


class DatasetCreate(BaseModel):
    """Bước 1: Định nghĩa tập dữ liệu + lược đồ."""

    data_source_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=1000)
    schema_fields: List[SchemaFieldSchema] = Field(..., min_length=1)


class DatasetSchemaUpdate(BaseModel):
    """Định nghĩa lại lược đồ của tập dữ liệu đã có."""

    schema_fields: List[SchemaFieldSchema] = Field(..., min_length=1)


class DatasetPartitioningConfigure(BaseModel):
    """Bước 2: Khai báo khoá chính + chiến lược phân mảnh."""

    primary_key: List[str] = Field(..., min_length=1)
    partition_strategy: str = Field(..., pattern=_PARTITION_STRATEGY_PATTERN)
    partition_column: Optional[str] = Field(None, max_length=255)


class CriticalFieldsDeclare(BaseModel):
    """Bước 3: Khai báo trường bắt buộc (NOT NULL)."""

    field_names: List[str] = Field(..., min_length=1)


class DatasetResponse(BaseModel):
    id: int
    data_source_id: int
    code: str
    name: str
    description: str
    schema_fields: List[Dict[str, Any]]
    primary_key: List[str]
    partition_strategy: str
    partition_column: Optional[str] = None
    current_schema_version: int
    is_active: bool

    model_config = {"from_attributes": True}


class CriticalFieldResponse(BaseModel):
    id: int
    dataset_id: int
    field_name: str

    model_config = {"from_attributes": True}


class SchemaVersionResponse(BaseModel):
    """Bước 4: 1 phiên bản lược đồ đã đăng ký vào Schema Registry."""

    id: int
    dataset_id: int
    version: int
    schema_snapshot: Dict[str, Any]
    registered_at: str

    model_config = {"from_attributes": True}


# ---------- UC-019: Cấu hình tác vụ điều phối ----------

_SYNC_MODE_PATTERN = "^(FULL|INCREMENTAL)$"
_RETRY_BACKOFF_PATTERN = "^(NONE|FIXED|EXPONENTIAL)$"
_RUN_STATUS_PATTERN = "^(IDLE|RUNNING|SUCCESS|FAILED)$"


class ScheduledTaskCreate(BaseModel):
    """Cấu hình tác vụ điều phối mới (lịch cron, đầy đủ/tăng dần, chính
    sách thử lại)."""

    dataset_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    sync_mode: str = Field("FULL", pattern=_SYNC_MODE_PATTERN)
    cron_expression: str = Field("0 0 * * *", min_length=1, max_length=100)
    retry_max_attempts: int = Field(3, ge=0)
    retry_delay_seconds: int = Field(60, ge=0)
    retry_backoff: str = Field("FIXED", pattern=_RETRY_BACKOFF_PATTERN)

    @field_validator("cron_expression")
    @classmethod
    def _validate_cron_expression(cls, value: str) -> str:
        if len(value.strip().split()) != 5:
            raise ValueError(
                "Lịch cron không hợp lệ, phải có đúng 5 trường "
                "(phút giờ ngày-trong-tháng tháng ngày-trong-tuần)"
            )
        return value


class ScheduledTaskConfigUpdate(BaseModel):
    """Sửa cấu hình tác vụ điều phối đã có."""

    sync_mode: str = Field(..., pattern=_SYNC_MODE_PATTERN)
    cron_expression: str = Field(..., min_length=1, max_length=100)
    retry_max_attempts: int = Field(..., ge=0)
    retry_delay_seconds: int = Field(..., ge=0)
    retry_backoff: str = Field(..., pattern=_RETRY_BACKOFF_PATTERN)

    @field_validator("cron_expression")
    @classmethod
    def _validate_cron_expression(cls, value: str) -> str:
        if len(value.strip().split()) != 5:
            raise ValueError(
                "Lịch cron không hợp lệ, phải có đúng 5 trường "
                "(phút giờ ngày-trong-tháng tháng ngày-trong-tuần)"
            )
        return value


class ScheduledTaskRunStatusUpdate(BaseModel):
    """Hệ thống (Bộ điều phối) cập nhật trạng thái thực thi tác vụ."""

    status: str = Field(..., pattern=_RUN_STATUS_PATTERN)
    message: str = Field("", max_length=2000)
    run_at: Optional[str] = None


class ScheduledTaskResponse(BaseModel):
    id: int
    dataset_id: int
    code: str
    name: str
    sync_mode: str
    cron_expression: str
    retry_max_attempts: int
    retry_delay_seconds: int
    retry_backoff: str
    is_enabled: bool
    status: str
    last_run_at: Optional[str] = None
    last_run_message: str

    model_config = {"from_attributes": True}


# ---------- UC-020: Xem lịch đầy đủ dữ liệu + lịch sử chạy ----------

_TRIGGER_PATTERN = "^(MANUAL|SCHEDULED|RETRY)$"
_RUN_FULL_STATUS_PATTERN = "^(RUNNING|SUCCESS|FAILED|PARTIAL)$"
_RUN_COMPLETE_STATUS_PATTERN = "^(SUCCESS|FAILED|PARTIAL)$"
_LOG_LEVEL_PATTERN = "^(INFO|WARNING|ERROR)$"


class IngestionRunStart(BaseModel):
    """Bắt đầu 1 phiên ingest mới (dùng bởi UC-021/UC-025 hoặc kích hoạt
    thủ công để kiểm thử)."""

    dataset_id: int = Field(..., gt=0)
    scheduled_task_id: Optional[int] = Field(None, gt=0)
    trigger: str = Field("MANUAL", pattern=_TRIGGER_PATTERN)
    sync_mode: str = Field("FULL", pattern=_SYNC_MODE_PATTERN)
    started_at: Optional[str] = None


class IngestionRunLogAppend(BaseModel):
    level: str = Field("INFO", pattern=_LOG_LEVEL_PATTERN)
    message: str = Field(..., min_length=1, max_length=4000)
    timestamp: Optional[str] = None


class IngestionRunComplete(BaseModel):
    status: str = Field(..., pattern=_RUN_COMPLETE_STATUS_PATTERN)
    records_read: int = Field(0, ge=0)
    records_loaded: int = Field(0, ge=0)
    records_failed: int = Field(0, ge=0)
    control_totals: Dict[str, Any] = Field(default_factory=dict)
    error_message: str = Field("", max_length=4000)
    finished_at: Optional[str] = None


class IngestionRunLogEntryResponse(BaseModel):
    timestamp: str
    level: str
    message: str


class IngestionRunResponse(BaseModel):
    id: int
    dataset_id: int
    scheduled_task_id: Optional[int] = None
    trigger: str
    sync_mode: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    records_read: int
    records_loaded: int
    records_failed: int
    control_totals: Dict[str, Any]
    error_message: str
    log_entries: List[Dict[str, str]]
    retry_of_run_id: Optional[int] = None

    model_config = {"from_attributes": True}


class IngestionRunListItemResponse(BaseModel):
    """Bản rút gọn cho danh sách lịch sử chạy (không kèm log_entries đầy
    đủ để danh sách nhẹ hơn; xem chi tiết log qua `GET /{run_id}`)."""

    id: int
    dataset_id: int
    scheduled_task_id: Optional[int] = None
    trigger: str
    sync_mode: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    records_read: int
    records_loaded: int
    records_failed: int
    error_message: str
    retry_of_run_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ---------- UC-021: Chạy lại phiên ingest lỗi ----------


class IngestionRunFailureReasonResponse(BaseModel):
    """Bước 1 UC-021: hệ thống hiển thị nguyên nhân của 1 phiên bị lỗi."""

    run_id: int
    dataset_id: int
    status: str
    error_message: str
    records_read: int
    records_loaded: int
    records_failed: int
    error_log_entries: List[Dict[str, str]]
    retryable: bool

    model_config = {"from_attributes": True}


class CalendarDayResponse(BaseModel):
    date: str
    run_count: int
    success_count: int
    failed_count: int
    running_count: int
    partial_count: int
    is_missing: bool

    model_config = {"from_attributes": True}

# ---------- UC-025: Đồng bộ tăng dần từ API/DB ----------

_INCREMENTAL_TRIGGER_PATTERN = "^(MANUAL|SCHEDULED)$"


class IncrementalSyncTrigger(BaseModel):
    """Kích hoạt 1 phiên đồng bộ tăng dần cho 1 tập dữ liệu. `trigger`
    mặc định `SCHEDULED` (Bộ điều phối tự động); dùng `MANUAL` khi kích
    hoạt thủ công để kiểm thử/chạy bù."""

    scheduled_task_id: Optional[int] = Field(None, gt=0)
    trigger: str = Field("SCHEDULED", pattern=_INCREMENTAL_TRIGGER_PATTERN)


class IncrementalSyncCheckpointResponse(BaseModel):
    """Điểm kiểm tra (checkpoint) hiện tại đọc từ ingestion.runs (bước 1)."""

    dataset_id: int
    checkpoint: Optional[str] = None


# ---------- UC-022: Tiếp nhận file thủ công TABMIS (upload) ----------
# ---------- UC-023: Xem trạng thái + sửa lỗi intake TABMIS ----------

_TABMIS_INTAKE_STATUS_PATTERN = "^(RECEIVED|TEMPLATE_INVALID|ROW_ERRORS|CORRECTED)$"


class TabmisIntakeSessionResponse(BaseModel):
    id: int
    dataset_id: int
    file_name: str
    raw_object_key: str
    status: str
    control_totals: Dict[str, Any]
    error_message: str
    uploaded_by: str
    uploaded_at: str
    ingestion_run_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TabmisIntakeRowErrorResponse(BaseModel):
    id: int
    session_id: int
    row_number: int
    field_name: str
    message: str

    model_config = {"from_attributes": True}


class TabmisIntakeStatusResponse(BaseModel):
    """UC-023 bước 1: trạng thái tiếp nhận + máy trạng thái (các hành động
    còn hợp lệ từ trạng thái hiện tại)."""

    session: TabmisIntakeSessionResponse
    allowed_actions: List[str]
    row_error_count: int


# ---------- UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (upload định kỳ) ----------

_VAN_BAN_INTAKE_STATUS_PATTERN = "^(RECEIVED|DUPLICATE_SKIPPED)$"


class VanBanIntakeResponse(BaseModel):
    id: int
    data_source_id: int
    so_ky_hieu: str
    loai_van_ban: str
    trich_yeu: str
    ngay_ban_hanh: str
    don_vi_ban_hanh: str
    raw_object_key: str
    status: str
    ocr_event_published: bool
    uploaded_by: str
    uploaded_at: str

    model_config = {"from_attributes": True}