"""Implementation tạm thời của cổng `KpiExplanationGenerator`.

`RuleBasedKpiExplanationGenerator` sinh lời giải thích bằng quy tắc suy
luận trên số liệu (KHÔNG gọi LLM thật) — dùng làm "AI Bộ điều phối" tối
thiểu cho UC-048. Khi UC-084..089 (quản trị mẫu prompt, định tuyến mô
hình, lập chỉ mục Vector Store) và UC-076 được triển khai, thay
implementation này bằng 1 client gọi LLM thật (vd. `LlmKpiExplanationGenerator`
dùng prompt template + model routing) — chỉ cần đổi factory ở router,
không cần sửa `application`/`interfaces`.
"""
from typing import Any, Dict, List

from app.domain.repositories import KpiExplanationGenerator

_MODEL_NAME = "rule-based-kpi-explainer-v1"


def _fmt_number(value: float) -> str:
    if value is None:
        return "n/a"
    if float(value).is_integer():
        return f"{value:,.0f}".replace(",", ".")
    return f"{value:,.2f}".replace(",", ".")


class RuleBasedKpiExplanationGenerator(KpiExplanationGenerator):
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        kpi_name = context.get("kpi_name", "KPI")
        dashboard_name = context.get("dashboard_name")
        unit = context.get("unit_of_measure") or ""
        year = context.get("year")
        org_unit = context.get("org_unit_code")
        sector = context.get("sector")
        current_value = context.get("current_value")
        prior_value = context.get("prior_value")
        delta_percent = context.get("delta_percent")
        breakdown: List[Dict[str, Any]] = context.get("breakdown") or []

        sentences = []

        scope_bits = []
        if year:
            scope_bits.append(f"năm {year}")
        if org_unit:
            scope_bits.append(f"đơn vị {org_unit}")
        if sector:
            scope_bits.append(f"lĩnh vực {sector}")
        scope_text = (", ".join(scope_bits)) if scope_bits else "phạm vi đang chọn"

        header = f"Chỉ tiêu \"{kpi_name}\""
        if dashboard_name:
            header += f" trên Bảng điều khiển \"{dashboard_name}\""
        sentences.append(
            f"{header} tại {scope_text} hiện đạt {_fmt_number(current_value)} {unit}."
        )

        if prior_value is not None and delta_percent is not None:
            if delta_percent > 0:
                direction = f"tăng {abs(delta_percent):.1f}%"
            elif delta_percent < 0:
                direction = f"giảm {abs(delta_percent):.1f}%"
            else:
                direction = "không đổi"
            sentences.append(
                f"So với cùng kỳ năm trước ({_fmt_number(prior_value)} {unit}), "
                f"chỉ tiêu này {direction}."
            )

        if breakdown:
            sorted_rows = sorted(
                breakdown, key=lambda r: abs(r.get("value") or 0), reverse=True
            )
            top = sorted_rows[0]
            sentences.append(
                f"Trong phân rã chi tiết, \"{top.get('label')}\" đóng góp lớn nhất với "
                f"{_fmt_number(top.get('value'))} {unit} "
                f"({len(sorted_rows)} thành phần được phân rã)."
            )

        sentences.append(
            "Đây là giải thích tự động dựa trên số liệu hiện có, chỉ mang tính "
            "tham khảo ban đầu — cần đối chiếu thêm với báo cáo nghiệp vụ chi tiết."
        )

        return {"explanation": " ".join(sentences), "model": _MODEL_NAME}