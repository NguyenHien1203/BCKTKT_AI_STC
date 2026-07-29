from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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