"""Infrastructure — UC-050 bước 1: "Sinh báo cáo theo mẫu + bộ lọc ->
Hệ thống truy vấn Lớp ngữ nghĩa + kết xuất".

`NoOpSemanticLayerReportQueryClient` sinh dữ liệu mẫu XÁC ĐỊNH
(deterministic, dựa trên hash MD5 của mã mẫu báo cáo + tên cột + bộ lọc +
số thứ tự dòng) — KHÔNG gọi Lớp ngữ nghĩa/CSDL thật, chỉ để luồng
"sinh + kết xuất báo cáo" chạy được ngay khi chưa tích hợp thật. Số dòng
sinh ra phụ thuộc vào bộ lọc (có đơn vị cụ thể thì ít dòng hơn) để mô
phỏng đúng ngữ nghĩa "áp bộ lọc thu hẹp kết quả".

Khi tích hợp thật: thay bằng client gọi Lớp ngữ nghĩa (semantic layer,
UC-043 `SemanticIndicatorService` ở `data-quality-service`, hoặc trực
tiếp Superset Chart Data API như `superset_query_client.py` của UC-048)
lấy đúng dữ liệu theo `template.columns` + bộ lọc — chỉ cần đổi factory
`get_semantic_layer_report_query_client()` bên dưới, không cần sửa
application/domain layer.
"""
import hashlib
from typing import Any, Dict, List

from app.domain.entities import ReportFilterConfig, ReportTemplate
from app.domain.repositories import SemanticLayerReportQueryClient

_NUMERIC_TYPES = {"INTEGER", "BIGINT", "DECIMAL", "FLOAT", "NUMBER"}
_DON_VI_MAU = [
    "Sở Tài chính",
    "Sở Kế hoạch và Đầu tư",
    "UBND Huyện A",
    "UBND Huyện B",
    "UBND Thành phố",
]


def _deterministic_value(seed: str, data_type: str, field_name: str) -> Any:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    data_type_upper = (data_type or "").upper()
    if data_type_upper in _NUMERIC_TYPES:
        return round((number % 1_000_000) / 100, 2)
    if data_type_upper == "DATE":
        return f"2026-{(number % 12) + 1:02d}-{(number % 28) + 1:02d}"
    if data_type_upper == "BOOLEAN":
        return bool(number % 2)
    if "don_vi" in field_name or "chu_dau_tu" in field_name:
        return _DON_VI_MAU[number % len(_DON_VI_MAU)]
    return f"{field_name} #{digest[:6]}"


class NoOpSemanticLayerReportQueryClient(SemanticLayerReportQueryClient):
    def query_report_rows(
        self, template: ReportTemplate, filters: ReportFilterConfig
    ) -> List[Dict[str, Any]]:
        # Có đơn vị cụ thể -> thu hẹp còn ít dòng hơn, mô phỏng đúng ngữ
        # nghĩa "áp bộ lọc". Không có -> trả nhiều dòng hơn (toàn ngành).
        row_count = 5 if filters.org_unit_code else 10

        filter_key = (
            f"{filters.year}:{filters.period_type}:{filters.period_value}:"
            f"{filters.org_unit_code or ''}:{filters.sector or ''}"
        )

        rows: List[Dict[str, Any]] = []
        for row_index in range(row_count):
            row: Dict[str, Any] = {}
            for column in template.columns:
                field_name = column.get("field")
                data_type = column.get("data_type", "STRING")
                seed = f"{template.code}:{filter_key}:{field_name}:{row_index}"
                row[field_name] = _deterministic_value(seed, data_type, field_name)
            rows.append(row)
        return rows


def get_semantic_layer_report_query_client() -> SemanticLayerReportQueryClient:
    return NoOpSemanticLayerReportQueryClient()