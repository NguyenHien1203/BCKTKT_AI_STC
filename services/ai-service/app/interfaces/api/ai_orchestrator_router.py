from fastapi import APIRouter, HTTPException

from app.application.use_cases.generate_kpi_explanation import (
    KpiExplanationOrchestratorService,
)
from app.domain.exceptions import DomainError, InvalidKpiExplanationRequest
from app.infrastructure.kpi_explanation_generator import (
    RuleBasedKpiExplanationGenerator,
)
from app.interfaces.api.schemas import (
    ErrorResponse,
    KpiExplanationContext,
    KpiExplanationResponse,
)

router = APIRouter(prefix="/ai-orchestrator", tags=["AI Bộ điều phối"])


def get_orchestrator_service() -> KpiExplanationOrchestratorService:
    # Đổi factory ở đây (thay `RuleBasedKpiExplanationGenerator`) khi tích
    # hợp LLM thật cho UC-076/084..089 — không cần sửa router/application.
    return KpiExplanationOrchestratorService(RuleBasedKpiExplanationGenerator())


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 422 if isinstance(exc, InvalidKpiExplanationRequest) else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "/kpi-explanations",
    response_model=KpiExplanationResponse,
    responses={422: {"model": ErrorResponse}},
)
def explain_kpi(payload: KpiExplanationContext):
    """Điểm vào "AI Bộ điều phối": nhận ngữ cảnh 1 KPI (giá trị hiện tại,
    phân rã chi tiết, so sánh cùng kỳ năm trước) và trả về lời giải thích.

    Dùng bởi UC-048 (Áp bộ lọc + xem chi tiết Bảng điều khiển, bước "Yêu
    cầu AI giải thích KPI") — reporting-service gọi HTTP sang endpoint này.
    """
    service = get_orchestrator_service()
    try:
        result = service.explain_kpi(payload.model_dump())
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return result