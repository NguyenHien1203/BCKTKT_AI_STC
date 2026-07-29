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
