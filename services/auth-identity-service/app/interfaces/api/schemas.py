from typing import Optional

from pydantic import BaseModel, Field


class OrgUnitCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    unit_type: str = Field(..., pattern="^(SO|PHONG|XA)$")
    parent_id: Optional[int] = None


class OrgUnitRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgUnitResponse(BaseModel):
    id: int
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int]
    is_active: bool

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    code: str
    message: str
