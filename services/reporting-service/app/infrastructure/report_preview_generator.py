"""Infrastructure — UC-049 bước 2: "Chọn mẫu báo cáo -> Hệ thống hiển thị
xem trước".

`NoOpReportPreviewGenerator` sinh dữ liệu mẫu XÁC ĐỊNH (deterministic, dựa
trên hash MD5 của mã mẫu báo cáo + tên cột + số thứ tự dòng) — KHÔNG truy
vấn Lớp ngữ nghĩa/CSDL thật, chỉ để giao diện có gì đó hiển thị "xem
trước" ngay khi chưa tích hợp UC-050 thật.

Khi tích hợp thật: thay bằng client gọi Lớp ngữ nghĩa (semantic layer,
UC-043 `SemanticIndicatorService`) lấy vài bản ghi mẫu đầu tiên theo đúng
`template.columns` — chỉ cần đổi factory `get_report_preview_generator()`
bên dưới, không cần sửa application/domain layer.
"""
import hashlib
from typing import Any, Dict, List

from app.domain.entities import ReportTemplate
from app.domain.repositories import ReportPreviewGenerator

_NUMERIC_TYPES = {"INTEGER", "BIGINT", "DECIMAL", "FLOAT", "NUMBER"}


def _deterministic_value(seed: str, data_type: str) -> Any:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    data_type_upper = (data_type or "").upper()
    if data_type_upper in _NUMERIC_TYPES:
        return round((number % 1_000_000) / 100, 2)
    if data_type_upper == "DATE":
        return f"2026-{(number % 12) + 1:02d}-{(number % 28) + 1:02d}"
    if data_type_upper == "BOOLEAN":
        return bool(number % 2)
    return f"Mẫu {digest[:6]}"


class NoOpReportPreviewGenerator(ReportPreviewGenerator):
    def generate_sample_rows(
        self, template: ReportTemplate, sample_size: int = 5
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for row_index in range(max(sample_size, 0)):
            row: Dict[str, Any] = {}
            for column in template.columns:
                field_name = column.get("field")
                data_type = column.get("data_type", "STRING")
                seed = f"{template.code}:{field_name}:{row_index}"
                row[field_name] = _deterministic_value(seed, data_type)
            rows.append(row)
        return rows


def get_report_preview_generator() -> ReportPreviewGenerator:
    return NoOpReportPreviewGenerator()