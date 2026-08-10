"""Application layer — UC-048: Áp bộ lọc + xem chi tiết Bảng điều khiển.

Đối chiếu docs/use_cases.json id=48: actor "Lãnh đạo Sở Tài chính, Cán bộ
tổng hợp Sở TC". Luồng:
  1. Áp bộ lọc Bảng điều khiển (năm, đơn vị, lĩnh vực) -> hệ thống truy vấn
     lại qua Superset.
  2. Xem chi tiết KPI -> hệ thống hiển thị phân rã chi tiết.
  3. So sánh cùng kỳ năm trước -> hệ thống truy thêm metric so sánh.
  4. Yêu cầu AI giải thích KPI -> hệ thống gọi AI Bộ điều phối.

`DashboardKpiService.register` là nghiệp vụ hỗ trợ để 1 dashboard có danh
mục KPI (giống `DashboardService.register` của UC-047) — bản thân UC-048
chỉ có thao tác lọc/xem/so sánh/yêu cầu AI giải thích.
"""
from typing import Any, Dict, List

from app.domain.entities import Dashboard, DashboardFilter, DashboardKpi, KpiExplanation
from app.domain.exceptions import (
    AIOrchestratorCallFailed,
    DashboardKpiCodeAlreadyExists,
    DashboardKpiNotFound,
    DashboardNotFound,
)
from app.domain.repositories import (
    AIOrchestratorClient,
    DashboardKpiRepository,
    DashboardRepository,
    KpiExplanationRepository,
    SupersetDashboardQueryClient,
)


class DashboardKpiService:
    """Quản lý danh mục KPI thuộc 1 Bảng điều khiển (nghiệp vụ hỗ trợ)."""

    def __init__(self, kpi_repo: DashboardKpiRepository, dashboard_repo: DashboardRepository):
        self._kpi_repo = kpi_repo
        self._dashboard_repo = dashboard_repo

    def register(
        self,
        dashboard_id: int,
        code: str,
        name: str,
        unit_of_measure: str,
        higher_is_better: bool = True,
    ) -> DashboardKpi:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        if self._kpi_repo.get_by_code(dashboard_id, code):
            raise DashboardKpiCodeAlreadyExists(dashboard_id, code)

        kpi = DashboardKpi(
            id=None,
            dashboard_id=dashboard_id,
            code=code.strip(),
            name=name.strip(),
            unit_of_measure=(unit_of_measure or "").strip(),
            higher_is_better=higher_is_better,
            is_active=True,
        )
        return self._kpi_repo.add(kpi)

    def list_for_dashboard(self, dashboard_id: int, only_active: bool = True) -> List[DashboardKpi]:
        return self._kpi_repo.list(dashboard_id, only_active=only_active)

    def get(self, dashboard_id: int, kpi_code: str) -> DashboardKpi:
        kpi = self._kpi_repo.get_by_code(dashboard_id, kpi_code)
        if kpi is None:
            raise DashboardKpiNotFound(dashboard_id, kpi_code)
        return kpi


class DashboardFilterQueryService:
    """Bước 1-3 của UC-048: áp bộ lọc, xem chi tiết KPI, so sánh cùng kỳ."""

    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        kpi_repo: DashboardKpiRepository,
        query_client: SupersetDashboardQueryClient,
    ):
        self._dashboard_repo = dashboard_repo
        self._kpi_repo = kpi_repo
        self._query_client = query_client

    def _get_dashboard(self, dashboard_id: int) -> Dashboard:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        return dashboard

    def _get_kpi(self, dashboard_id: int, kpi_code: str) -> DashboardKpi:
        kpi = self._kpi_repo.get_by_code(dashboard_id, kpi_code)
        if kpi is None:
            raise DashboardKpiNotFound(dashboard_id, kpi_code)
        return kpi

    def apply_filters(
        self, dashboard_id: int, filters: DashboardFilter
    ) -> Dict[str, Any]:
        """Bước 1 — "Áp bộ lọc Bảng điều khiển (năm, đơn vị, lĩnh vực)":
        hệ thống truy vấn lại qua Superset, trả về giá trị từng KPI đang
        active của dashboard theo đúng bộ lọc."""
        dashboard = self._get_dashboard(dashboard_id)
        kpis = self._kpi_repo.list(dashboard_id, only_active=True)
        values = self._query_client.query_kpi_values(dashboard, kpis, filters)
        return {
            "dashboard_id": dashboard.id,
            "filters": filters,
            "kpi_values": [
                {
                    "kpi_code": kpi.code,
                    "kpi_name": kpi.name,
                    "unit_of_measure": kpi.unit_of_measure,
                    "value": values.get(kpi.code),
                }
                for kpi in kpis
            ],
        }

    def get_kpi_detail(
        self, dashboard_id: int, kpi_code: str, filters: DashboardFilter
    ) -> Dict[str, Any]:
        """Bước 2 — "Xem chi tiết KPI": hệ thống hiển thị phân rã chi tiết."""
        dashboard = self._get_dashboard(dashboard_id)
        kpi = self._get_kpi(dashboard_id, kpi_code)
        values = self._query_client.query_kpi_values(dashboard, [kpi], filters)
        breakdown = self._query_client.query_kpi_breakdown(dashboard, kpi, filters)
        return {
            "dashboard_id": dashboard.id,
            "kpi_code": kpi.code,
            "kpi_name": kpi.name,
            "unit_of_measure": kpi.unit_of_measure,
            "filters": filters,
            "value": values.get(kpi.code),
            "breakdown": breakdown,
        }

    def compare_with_prior_year(
        self, dashboard_id: int, kpi_code: str, filters: DashboardFilter
    ) -> Dict[str, Any]:
        """Bước 3 — "So sánh cùng kỳ năm trước": hệ thống truy thêm metric
        so sánh (truy vấn lại Superset với `year - 1`)."""
        dashboard = self._get_dashboard(dashboard_id)
        kpi = self._get_kpi(dashboard_id, kpi_code)

        current_values = self._query_client.query_kpi_values(dashboard, [kpi], filters)
        current_value = current_values.get(kpi.code)
        prior_value = self._query_client.query_kpi_prior_year_value(dashboard, kpi, filters)

        delta = None
        delta_percent = None
        if current_value is not None and prior_value is not None:
            delta = current_value - prior_value
            delta_percent = (delta / prior_value * 100) if prior_value else None

        return {
            "dashboard_id": dashboard.id,
            "kpi_code": kpi.code,
            "kpi_name": kpi.name,
            "unit_of_measure": kpi.unit_of_measure,
            "filters": filters,
            "current_year": filters.year,
            "current_value": current_value,
            "prior_year": filters.year - 1,
            "prior_value": prior_value,
            "delta": delta,
            "delta_percent": delta_percent,
        }


class KpiExplanationService:
    """Bước 4 của UC-048: "Yêu cầu AI giải thích KPI" -> "Hệ thống gọi AI
    Bộ điều phối"."""

    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        kpi_repo: DashboardKpiRepository,
        explanation_repo: KpiExplanationRepository,
        query_client: SupersetDashboardQueryClient,
        ai_orchestrator_client: AIOrchestratorClient,
    ):
        self._dashboard_repo = dashboard_repo
        self._kpi_repo = kpi_repo
        self._explanation_repo = explanation_repo
        self._query_client = query_client
        self._ai_orchestrator_client = ai_orchestrator_client

    def request_explanation(
        self, dashboard_id: int, kpi_code: str, filters: DashboardFilter, requested_by: int
    ) -> KpiExplanation:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        kpi = self._kpi_repo.get_by_code(dashboard_id, kpi_code)
        if kpi is None:
            raise DashboardKpiNotFound(dashboard_id, kpi_code)

        # Dựng lại ngữ cảnh đầy đủ (giá trị hiện tại + phân rã + so sánh
        # cùng kỳ năm trước) trước khi gọi AI Bộ điều phối, để lời giải
        # thích bám sát đúng số liệu người dùng đang xem trên màn hình.
        current_values = self._query_client.query_kpi_values(dashboard, [kpi], filters)
        current_value = current_values.get(kpi.code)
        breakdown = self._query_client.query_kpi_breakdown(dashboard, kpi, filters)
        prior_value = self._query_client.query_kpi_prior_year_value(dashboard, kpi, filters)
        delta_percent = None
        if current_value is not None and prior_value:
            delta_percent = (current_value - prior_value) / prior_value * 100

        context: Dict[str, Any] = {
            "kpi_code": kpi.code,
            "kpi_name": kpi.name,
            "dashboard_name": dashboard.name,
            "unit_of_measure": kpi.unit_of_measure,
            "year": filters.year,
            "org_unit_code": filters.org_unit_code,
            "sector": filters.sector,
            "current_value": current_value,
            "prior_value": prior_value,
            "delta_percent": delta_percent,
            "breakdown": breakdown,
        }

        try:
            result = self._ai_orchestrator_client.explain_kpi(context)
        except AIOrchestratorCallFailed:
            raise
        except Exception as exc:  # pragma: no cover - lỗi hạ tầng bất định
            raise AIOrchestratorCallFailed(str(exc)) from exc

        explanation = KpiExplanation(
            id=None,
            dashboard_id=dashboard_id,
            kpi_code=kpi.code,
            year=filters.year,
            org_unit_code=filters.org_unit_code,
            sector=filters.sector,
            requested_by=requested_by,
            explanation=result.get("explanation", ""),
            model=result.get("model", ""),
        )
        return self._explanation_repo.add(explanation)

    def list_explanations(self, dashboard_id: int, kpi_code: str) -> List[KpiExplanation]:
        return self._explanation_repo.list(dashboard_id, kpi_code)