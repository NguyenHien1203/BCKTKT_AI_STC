"""Sinh báo cáo ATTT (an toàn thông tin) định kỳ dạng PDF (UC-09).

Dùng `reportlab` (Platypus) — thư viện chuẩn cho tạo PDF, không phụ thuộc
mạng khi cài đặt. Implement cổng `AuditReportGenerator` khai báo ở
domain/repositories.py.
"""
from io import BytesIO
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.entities import AuditLogEntry
from app.domain.repositories import AuditReportGenerator


class ReportLabAuditReportGenerator(AuditReportGenerator):
    def generate(
        self,
        entries: List[AuditLogEntry],
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

        story.append(Paragraph("BÁO CÁO AN TOÀN THÔNG TIN (ATTT) ĐỊNH KỲ", styles["Title"]))
        story.append(Spacer(1, 6))
        story.append(
            Paragraph(
                "Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Nhật ký truy cập và thao tác",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        khoang_thoi_gian = f"{time_from or 'không giới hạn'} — {time_to or 'không giới hạn'}"
        story.append(Paragraph(f"<b>Khoảng thời gian:</b> {khoang_thoi_gian}", styles["Normal"]))
        story.append(Paragraph(f"<b>Thời điểm sinh báo cáo:</b> {generated_at}", styles["Normal"]))
        story.append(Paragraph(f"<b>Tổng số bản ghi:</b> {len(entries)}", styles["Normal"]))
        story.append(Spacer(1, 14))

        header = ["Thời gian", "Tài khoản", "Hành động", "Đối tượng", "Trạng thái", "Địa chỉ IP"]
        data = [header]
        for entry in entries:
            resource = entry.resource_type
            if entry.resource_id:
                resource = f"{resource}#{entry.resource_id}"
            data.append(
                [
                    entry.created_at,
                    entry.username,
                    entry.action,
                    resource,
                    entry.status,
                    entry.ip_address or "-",
                ]
            )

        if len(data) == 1:
            story.append(Paragraph("Không có bản ghi nhật ký nào trong khoảng thời gian này.", styles["Normal"]))
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