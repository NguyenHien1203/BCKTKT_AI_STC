"""Application layer — "AI Bộ điều phối" tối thiểu, dùng bởi UC-048 (Áp bộ
lọc + xem chi tiết Bảng điều khiển, bước "Yêu cầu AI giải thích KPI") và
sẽ được UC-076 (AI giải thích KPI trên Bảng điều khiển, `todo`) MỞ RỘNG
sau (định tuyến mô hình UC-087, mẫu prompt UC-084..086, ghi AI Audit Log
UC-010) — không cần viết lại endpoint khi đó.

`KpiExplanationOrchestratorService.explain_kpi()` chỉ xác thực tối thiểu
(có `kpi_name`, có `current_value`) rồi giao cho cổng `KpiExplanationGenerator`
(hiện là `RuleBasedKpiExplanationGenerator`, xem
`app/infrastructure/kpi_explanation_generator.py`) sinh lời giải thích.
"""
from typing import Any, Dict

from app.domain.exceptions import InvalidKpiExplanationRequest
from app.domain.repositories import KpiExplanationGenerator


class KpiExplanationOrchestratorService:
    def __init__(self, generator: KpiExplanationGenerator):
        self._generator = generator

    def explain_kpi(self, context: Dict[str, Any]) -> Dict[str, str]:
        kpi_name = context.get("kpi_name")
        if not kpi_name or not str(kpi_name).strip():
            raise InvalidKpiExplanationRequest("Ngữ cảnh giải thích KPI phải có 'kpi_name'")
        if context.get("current_value") is None:
            raise InvalidKpiExplanationRequest(
                "Ngữ cảnh giải thích KPI phải có 'current_value'"
            )
        return self._generator.generate(context)