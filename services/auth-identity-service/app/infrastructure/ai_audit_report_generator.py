"""Sinh báo cáo AI Audit định kỳ tuần/tháng dạng PDF (UC-10).

Dùng `reportlab` (Platypus), cùng cách tiếp cận với UC-09
(`infrastructure/audit_report_generator.py`) nhưng nội dung/tiêu đề khác biệt
cho phù hợp báo cáo AI Audit. Implement cổng `AiAuditReportGenerator` khai
báo ở domain/repositories.py.
"""
from io import BytesIO
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.entities import AiAuditLogEntry
from app.domain.repositories import AiAuditReportGenerator

_PERIOD_LABEL = {"WEEK": "TUẦN", "MONTH": "THÁNG"}


class ReportLabAiAuditReportGenerator(AiAuditReportGenerator):
    def generate(
        self,
        entries: List[AiAuditLogEntry],
        period: str,
        time_from: Optional[str],
        time_to: Optional[str],
        generated_at: str,
    ) -> bytes:
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
        story = []

        period_label = _PERIOD_LABEL.get(period, period)
        story.append(Paragraph(f"BÁO CÁO AI AUDIT ĐỊNH KỲ ({period_label})", styles["Title"]))
        story.append(Spacer(1, 6))
        story.append(
            Paragraph(
                "Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Quản trị AI Audit Log",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        khoang_thoi_gian = f"{time_from or 'không giới hạn'} — {time_to or 'không giới hạn'}"
        story.append(Paragraph(f"<b>Khoảng thời gian:</b> {khoang_thoi_gian}", styles["Normal"]))
        story.append(Paragraph(f"<b>Thời điểm sinh báo cáo:</b> {generated_at}", styles["Normal"]))
        story.append(Paragraph(f"<b>Tổng số phiên hỏi-đáp AI:</b> {len(entries)}", styles["Normal"]))
        story.append(Spacer(1, 14))

        header = ["Thời gian", "Người dùng", "Mô hình", "Trace ID", "Số nguồn dẫn"]
        data = [header]
        for entry in entries:
            data.append(
                [
                    entry.created_at,
                    entry.username,
                    entry.model or "-",
                    entry.trace_id,
                    str(len(entry.sources or [])),
                ]
            )

        if len(data) == 1:
            story.append(
                Paragraph(
                    "Không có phiên hỏi-đáp AI nào trong khoảng thời gian này.", styles["Normal"]
                )
            )
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
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                    ]
                )
            )
            story.append(table)

        doc.build(story)
        return buffer.getvalue()