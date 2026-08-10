"""Implementation tạm thời của cổng `SupersetDashboardQueryClient`.

`NoOpSupersetDashboardQueryClient` KHÔNG gọi Superset thật — sinh dữ liệu
xác định (deterministic, dựa trên hash của dashboard/KPI/bộ lọc) để UC-048
có thể chạy + test được ngay mà chưa cần 1 Superset instance thật đã nạp
đủ dataset/chart. Khi tích hợp thật, thay bằng
`SupersetChartDataQueryClient` gọi `POST /api/v1/chart/data` (Superset
Chart Data API) với `extra_filters` dựng từ `DashboardFilter` (năm =
temporal filter, đơn vị/lĩnh vực = adhoc filter theo cột tương ứng) —
tái sử dụng `SupersetConfig`/đăng nhập tại `superset_client.py` (UC-047)
để lấy access_token, chỉ cần đổi factory ở router.
"""
import hashlib
from typing import Any, Dict, List, Optional

from app.domain.entities import Dashboard, DashboardFilter, DashboardKpi
from app.domain.repositories import SupersetDashboardQueryClient

_BREAKDOWN_LABELS = ["Đơn vị A", "Đơn vị B", "Đơn vị C", "Đơn vị D"]


def _deterministic_value(*parts: Any, base: float = 1000.0, spread: float = 800.0) -> float:
    """Sinh 1 giá trị số xác định (không đổi giữa các lần gọi cùng tham
    số) từ hash MD5 của các thành phần — mô phỏng 1 kết quả truy vấn
    Superset ổn định cho cùng 1 bộ lọc, phục vụ test/demo."""
    key = "|".join(str(p) for p in parts if p is not None)
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    fraction = int(digest[:8], 16) / 0xFFFFFFFF
    return round(base + fraction * spread, 2)


class NoOpSupersetDashboardQueryClient(SupersetDashboardQueryClient):
    def query_kpi_values(
        self, dashboard: Dashboard, kpis: List[DashboardKpi], filters: DashboardFilter
    ) -> Dict[str, float]:
        return {
            kpi.code: _deterministic_value(
                "value", dashboard.id, kpi.code, filters.year, filters.org_unit_code, filters.sector
            )
            for kpi in kpis
        }

    def query_kpi_breakdown(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> List[Dict[str, Any]]:
        rows = []
        for label in _BREAKDOWN_LABELS:
            value = _deterministic_value(
                "breakdown",
                dashboard.id,
                kpi.code,
                filters.year,
                filters.org_unit_code,
                filters.sector,
                label,
                base=100.0,
                spread=400.0,
            )
            rows.append({"label": label, "value": value})
        return rows

    def query_kpi_prior_year_value(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> Optional[float]:
        prior_filters = DashboardFilter(
            year=filters.year - 1,
            org_unit_code=filters.org_unit_code,
            sector=filters.sector,
        )
        return self.query_kpi_values(dashboard, [kpi], prior_filters).get(kpi.code)