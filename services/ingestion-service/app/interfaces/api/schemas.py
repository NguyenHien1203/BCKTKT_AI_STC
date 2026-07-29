from typing import Optional

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