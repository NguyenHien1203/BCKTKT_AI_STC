"""Pydantic schemas cho UC-058 — Quản lý danh mục API."""
from datetime import date, datetime
from typing import Optional

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