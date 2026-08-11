from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---------- "AI Bộ điều phối" — giải thích KPI (dùng bởi UC-048, UC-076) ----------


class KpiBreakdownItem(BaseModel):
    label: str
    value: Optional[float] = None


class KpiExplanationContext(BaseModel):
    kpi_code: Optional[str] = None
    kpi_name: str = Field(..., min_length=1)
    dashboard_name: Optional[str] = None
    unit_of_measure: Optional[str] = ""
    year: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    current_value: float
    prior_value: Optional[float] = None
    delta_percent: Optional[float] = None
    breakdown: List[KpiBreakdownItem] = Field(default_factory=list)
    extra: Optional[Dict[str, Any]] = None


class KpiExplanationResponse(BaseModel):
    explanation: str
    model: str


class ErrorResponse(BaseModel):
    code: str
    message: str