"""Sinh báo cáo nguồn gốc dữ liệu (data lineage/provenance) dạng PDF

(UC-046). Dùng `reportlab` (Platypus), cùng khuôn mẫu
`auth-identity-service/app/infrastructure/audit_report_generator.py`
(UC-09) -- không phụ thuộc mạng khi cài đặt.
"""
import json
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.application.use_cases.export_data_provenance_report import ProvenanceReport

_STEP_ORDER_LABELS = [
    ("RAW", "Thô"),
    ("PARSING", "Phân tích"),
    ("MAPPING", "Ánh xạ"),
    ("QUALITY", "Chất lượng"),
    ("PUBLISH", "Công bố"),
]


def _short_json(value: Any, max_chars: int = 500) -> str:
    if value is None:
        return "-"
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    if len(text) > max_chars:
        text = text[:max_chars] + " …"
    # tránh XML injection vỡ layout Paragraph của reportlab
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class ReportLabProvenanceReportGenerator:
    """Implement cổng sinh PDF cho `ProvenanceReport` (UC-046)."""

    def generate(self, report: ProvenanceReport) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        mono_style = ParagraphStyle(
            "Mono",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
        )
        story = []

        story.append(Paragraph("BÁO CÁO NGUỒN GỐC DỮ LIỆU", styles["Title"]))
        story.append(Spacer(1, 6))
        story.append(
            Paragraph(
                "Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Truy vết nguồn gốc dữ liệu (UC-046)",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        story.append(
            Paragraph(
                f"<b>Phạm vi báo cáo:</b> {report.scope_label} (mã = {report.scope_value})",
                styles["Normal"],
            )
        )
        story.append(Paragraph(f"<b>Thời điểm sinh báo cáo:</b> {report.generated_at}", styles["Normal"]))
        story.append(
            Paragraph(
                f"<b>Tổng số bản ghi khớp phạm vi:</b> {report.total_matched} — "
                f"<b>Số bản ghi trong báo cáo:</b> {report.returned_count}"
                + (" (đã cắt bớt, xem chi tiết đầy đủ theo từng bản ghi)" if report.truncated else ""),
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>Số bản ghi truy vết đầy đủ 5 bước (thô→phân tích→ánh xạ→chất lượng→công bố):</b> "
                f"{report.fully_traced_count}/{report.returned_count}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 14))

        header = ["Bản ghi (id)", "Tập dữ liệu", "Dòng #"] + [label for _, label in _STEP_ORDER_LABELS]
        data = [header]
        step_status_by_record = {}
        for rec in report.records:
            steps_by_code = {s.step: s for s in rec.chain.steps}
            step_status_by_record[rec.curated_dm_record_id] = steps_by_code
            row = [str(rec.curated_dm_record_id), str(rec.dataset_id or "-"), str(rec.row_index)]
            for code, _label in _STEP_ORDER_LABELS:
                step = steps_by_code.get(code)
                if step is None:
                    row.append("-")
                elif not step.available:
                    row.append("Thiếu")
                else:
                    row.append(step.status or "OK")
            data.append(row)

        if len(data) == 1:
            story.append(Paragraph("Không có bản ghi nào khớp phạm vi đã chọn.", styles["Normal"]))
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

        # Chi tiết từng bước (dữ liệu vào/ra + phép biến đổi) -- chỉ có khi
        # người gọi bật include_step_details (mặc định bật khi phạm vi RECORD).
        for rec in report.records:
            if not rec.step_details:
                continue
            story.append(Spacer(1, 16))
            story.append(
                Paragraph(
                    f"Chi tiết truy vết bản ghi curated #{rec.curated_dm_record_id} "
                    f"(tập dữ liệu {rec.dataset_id or '-'} — dòng #{rec.row_index})",
                    styles["Heading3"],
                )
            )
            for detail in rec.step_details:
                story.append(Spacer(1, 6))
                title = f"Bước: {detail.label} ({detail.step})"
                if not detail.available:
                    title += " — KHÔNG CÓ DỮ LIỆU"
                story.append(Paragraph(f"<b>{title}</b>", styles["Normal"]))
                if detail.note:
                    story.append(Paragraph(f"Ghi chú: {detail.note}", styles["Normal"]))
                if detail.transformation:
                    story.append(
                        Paragraph(f"Phép biến đổi: {detail.transformation}", styles["Normal"])
                    )
                story.append(Paragraph(f"Đầu vào: {_short_json(detail.input)}", mono_style))
                story.append(Paragraph(f"Đầu ra: {_short_json(detail.output)}", mono_style))
                if detail.meta:
                    story.append(Paragraph(f"Thông tin thêm: {_short_json(detail.meta)}", mono_style))

        doc.build(story)
        return buffer.getvalue()