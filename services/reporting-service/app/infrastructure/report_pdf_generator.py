"""Infrastructure — UC-050 bước 2: "Kết xuất PDF -> Hệ thống trả file".

Dùng `reportlab` (Platypus), cùng khuôn mẫu
`data-quality-service/app/infrastructure/provenance_report_generator.py`
(UC-046) và `auth-identity-service/app/infrastructure/audit_report_generator.py`
(UC-09) — không phụ thuộc mạng khi cài đặt.
"""
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.entities import ReportFilterConfig, ReportTemplate

_PERIOD_LABELS = {"THANG": "Tháng", "QUY": "Quý", "NAM": "Năm"}


def _format_filters(filters: ReportFilterConfig) -> str:
    parts = [f"Năm {filters.year}"]
    period_label = _PERIOD_LABELS.get(filters.period_type, filters.period_type)
    if filters.period_type == "NAM":
        parts.append(f"Kỳ: {period_label}")
    else:
        parts.append(f"Kỳ: {period_label} {filters.period_value}")
    if filters.org_unit_code:
        parts.append(f"Đơn vị: {filters.org_unit_code}")
    if filters.sector:
        parts.append(f"Lĩnh vực: {filters.sector}")
    return " | ".join(parts)


def _escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ReportLabReportPdfGenerator:
    """Implement cổng sinh PDF cho 1 báo cáo đã sinh theo mẫu + bộ lọc (UC-050)."""

    def generate(
        self,
        template: ReportTemplate,
        filters: ReportFilterConfig,
        rows: List[Dict[str, Any]],
    ) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=1.2 * cm,
            rightMargin=1.2 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(_escape(template.name), styles["Title"]))
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                "Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Sinh + kết xuất báo cáo (UC-050)",
                styles["Normal"],
            )
        )
        if template.description:
            story.append(Paragraph(_escape(template.description), styles["Normal"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Bộ lọc:</b> {_escape(_format_filters(filters))}", styles["Normal"]))
        story.append(Paragraph(f"<b>Tổng số dòng:</b> {len(rows)}", styles["Normal"]))
        story.append(Spacer(1, 12))

        columns = template.columns
        header = [c.get("label", c.get("field")) for c in columns]
        data = [header]
        for row in rows:
            data.append([_escape(row.get(c.get("field"))) for c in columns])

        if len(data) == 1:
            story.append(Paragraph("Không có dữ liệu khớp bộ lọc đã chọn.", styles["Normal"]))
        else:
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f3f4f6")],
                        ),
                    ]
                )
            )
            story.append(table)

        doc.build(story)
        return buffer.getvalue()