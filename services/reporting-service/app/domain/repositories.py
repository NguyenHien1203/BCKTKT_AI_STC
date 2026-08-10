"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    Dashboard,
    DashboardFavorite,
    DashboardFilter,
    DashboardKpi,
    KpiExplanation,
)


class DashboardRepository(ABC):
    """Repository cho UC-047: danh mục Bảng điều khiển điều hành."""

    @abstractmethod
    def add(self, dashboard: Dashboard) -> Dashboard:
        ...

    @abstractmethod
    def get_by_id(self, dashboard_id: int) -> Optional[Dashboard]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Dashboard]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        category: Optional[str] = None,
    ) -> List[Dashboard]:
        ...

    @abstractmethod
    def update(self, dashboard: Dashboard) -> Dashboard:
        ...


class DashboardFavoriteRepository(ABC):
    """Repository cho UC-047: tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích"."""

    @abstractmethod
    def add(self, favorite: DashboardFavorite) -> DashboardFavorite:
        ...

    @abstractmethod
    def get(self, user_id: int, dashboard_id: int) -> Optional[DashboardFavorite]:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[DashboardFavorite]:
        ...

    @abstractmethod
    def delete(self, user_id: int, dashboard_id: int) -> bool:
        ...


class DashboardKpiRepository(ABC):
    """Repository cho UC-048: danh mục chỉ tiêu (KPI) thuộc 1 Bảng điều khiển."""

    @abstractmethod
    def add(self, kpi: DashboardKpi) -> DashboardKpi:
        ...

    @abstractmethod
    def get_by_code(self, dashboard_id: int, code: str) -> Optional[DashboardKpi]:
        ...

    @abstractmethod
    def list(self, dashboard_id: int, only_active: bool = True) -> List[DashboardKpi]:
        ...

    @abstractmethod
    def update(self, kpi: DashboardKpi) -> DashboardKpi:
        ...


class KpiExplanationRepository(ABC):
    """Repository cho UC-048: lịch sử "Yêu cầu AI giải thích KPI" (append-only)."""

    @abstractmethod
    def add(self, explanation: KpiExplanation) -> KpiExplanation:
        ...

    @abstractmethod
    def list(self, dashboard_id: int, kpi_code: str) -> List[KpiExplanation]:
        ...


class SupersetDashboardQueryClient(ABC):
    """Cổng (port) UC-048 bước 1-3: "Hệ thống truy vấn lại qua Superset"
    khi người dùng áp bộ lọc / xem chi tiết KPI / so sánh cùng kỳ năm
    trước. Triển khai thật (khi tích hợp) nên gọi Superset Chart Data API
    (`POST /api/v1/chart/data`) với `extra_filters` dựng từ
    `DashboardFilter` — xem `infrastructure/superset_query_client.py`.
    """

    @abstractmethod
    def query_kpi_values(
        self, dashboard: Dashboard, kpis: List[DashboardKpi], filters: DashboardFilter
    ) -> Dict[str, float]:
        """Bước 1-2: trả về `{kpi_code: giá_trị}` sau khi áp bộ lọc."""
        ...

    @abstractmethod
    def query_kpi_breakdown(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> List[Dict[str, Any]]:
        """Bước "Xem chi tiết KPI": trả về danh sách
        `{"label": str, "value": float}` — phân rã chi tiết theo đơn vị/
        khoản mục con."""
        ...

    @abstractmethod
    def query_kpi_prior_year_value(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> Optional[float]:
        """Bước "So sánh cùng kỳ năm trước": truy vấn lại với `year - 1`."""
        ...


class AIOrchestratorClient(ABC):
    """Cổng (port) UC-048 bước cuối: "Yêu cầu AI giải thích KPI" ->
    "Hệ thống gọi AI Bộ điều phối" (`ai-service`, endpoint
    `POST /ai-orchestrator/kpi-explanations`)."""

    @abstractmethod
    def explain_kpi(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Trả về `{"explanation": str, "model": str}`."""
        ...


class UserAccessContextProvider(ABC):
    """Cổng (port) tra cứu ngữ cảnh quyền của người dùng để dựng Row Level
    Security (RLS) filters nhúng vào guest token Superset — mỗi người dùng
    chỉ thấy đúng phạm vi dữ liệu được phép (vd: theo đơn vị/phòng ban),
    dù cùng xem chung 1 dashboard.

    Triển khai thật (khi tích hợp) nên gọi sang `auth-identity-service`
    UC-04 (permission_context: permitted_domains + đơn vị + mức nhạy cảm)
    để dựng danh sách RLS filter tương ứng. Xem infrastructure/user_access_context.py.
    """

    @abstractmethod
    def get_rls_filters(self, user_id: int) -> List[Dict[str, Any]]:
        """Trả về danh sách RLS clause dạng
        `{"dataset": <tên dataset Superset, tuỳ chọn>, "clause": "<SQL WHERE clause>"}`
        để nhúng vào guest token (tham số `rls` của Superset)."""
        ...


class GuestTokenIssuer(ABC):
    """Cổng (port) gọi Superset REST API để phát hành Guest Token — cách
    CHÍNH THỨC Superset hỗ trợ nhúng dashboard có kiểm soát quyền, thay cho
    nhúng iframe `embed_url` trực tiếp (không kiểm soát quyền theo người dùng).
    """

    @abstractmethod
    def issue(
        self,
        dashboard_uid: str,
        user_id: int,
        username: str,
        full_name: str,
        rls_filters: List[Dict[str, Any]],
    ) -> str:
        """Trả về guest token (JWT ngắn hạn do Superset ký) để frontend
        truyền cho `@superset-ui/embedded-sdk`."""
        ...