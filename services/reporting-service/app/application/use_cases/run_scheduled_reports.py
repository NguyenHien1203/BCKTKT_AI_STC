"""Application layer — UC-051 bước cuối: "Hệ thống tự động sinh + gửi
email báo cáo theo lịch" -> "Tác vụ định kỳ (cron)".

Tái sử dụng NGUYÊN VẸN `ReportGenerationService` (UC-050) để sinh dữ liệu
báo cáo (bước "Sinh báo cáo theo mẫu + bộ lọc" -> "Hệ thống truy vấn Lớp
ngữ nghĩa + kết xuất") + 2 bộ sinh file PDF/Excel đã có (UC-050 bước
2/3) — không viết lại. `ReportScheduleRunnerService` chỉ thêm phần: xác
định lịch nào "tới hạn" (bước tác vụ định kỳ) rồi gửi email đính kèm file
cho danh sách người nhận đã cấu hình (UC-051 bước 2), ghi lại
`ReportScheduleRunLog` (thành công/thất bại) sau mỗi lần chạy.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.application.use_cases.generate_and_export_report import ReportGenerationService
from app.domain.entities import ReportSchedule, ReportScheduleRunLog
from app.domain.exceptions import DomainError, NoReportScheduleRecipients, ReportEmailSendFailed
from app.domain.repositories import (
    ReportEmailSender,
    ReportScheduleRecipientRepository,
    ReportScheduleRepository,
    ReportScheduleRunLogRepository,
)
from app.infrastructure.report_excel_generator import OpenpyxlReportExcelGenerator
from app.infrastructure.report_pdf_generator import ReportLabReportPdfGenerator

_PERIOD_LABELS = {"THANG": "Tháng", "QUY": "Quý", "NAM": "Năm"}


def _is_due(schedule: ReportSchedule, now: datetime) -> bool:
    """Tới hạn khi (1) đã qua giờ chạy trong ngày (`time_of_day`) VÀ
    (2) đúng chu kỳ (hàng ngày: mỗi ngày; hàng tuần: đúng `day_of_week`;
    hàng tháng: đúng `day_of_month`, hoặc ngày cuối tháng nếu tháng đó
    ngắn hơn `day_of_month`) VÀ (3) chưa chạy lần nào trong đúng chu kỳ
    hiện tại (tránh chạy lặp lại nhiều lần trong cùng 1 ngày khi tác vụ
    định kỳ quét thường xuyên hơn 1 lần/ngày)."""
    hour, minute = (int(p) for p in schedule.time_of_day.split(":"))
    scheduled_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < scheduled_today:
        return False

    if schedule.frequency == "WEEKLY" and now.weekday() != schedule.day_of_week:
        return False
    if schedule.frequency == "MONTHLY" and now.day != schedule.day_of_month:
        return False

    if schedule.last_run_at is None:
        return True

    last_run = schedule.last_run_at
    if schedule.frequency == "DAILY":
        return last_run.date() < now.date()
    if schedule.frequency == "WEEKLY":
        return (now.date() - last_run.date()).days >= 1
    if schedule.frequency == "MONTHLY":
        return last_run.year != now.year or last_run.month != now.month
    return False


def _email_subject(schedule: ReportSchedule) -> str:
    return f"[Báo cáo định kỳ] Mẫu id={schedule.template_id} — {schedule.frequency}"


def _email_body(schedule: ReportSchedule, row_count: int, filters) -> str:
    period_label = _PERIOD_LABELS.get(filters.period_type, filters.period_type)
    period_desc = (
        period_label
        if filters.period_type == "NAM"
        else f"{period_label} {filters.period_value}"
    )
    lines = [
        "Hệ thống tự động sinh báo cáo theo lịch đã cấu hình (UC-051).",
        f"Bộ lọc: Năm {filters.year} — Kỳ: {period_desc}",
    ]
    if filters.org_unit_code:
        lines.append(f"Đơn vị: {filters.org_unit_code}")
    if filters.sector:
        lines.append(f"Lĩnh vực: {filters.sector}")
    lines.append(f"Tổng số dòng dữ liệu: {row_count}")
    lines.append("File báo cáo được đính kèm trong email này.")
    return "\n".join(lines)


class ReportScheduleRunnerService:
    def __init__(
        self,
        schedule_repo: ReportScheduleRepository,
        recipient_repo: ReportScheduleRecipientRepository,
        run_log_repo: ReportScheduleRunLogRepository,
        report_generation_service: ReportGenerationService,
        email_sender: ReportEmailSender,
    ):
        self._schedules = schedule_repo
        self._recipients = recipient_repo
        self._run_logs = run_log_repo
        self._report_generation = report_generation_service
        self._email_sender = email_sender
        self._pdf_generator = ReportLabReportPdfGenerator()
        self._excel_generator = OpenpyxlReportExcelGenerator()

    def _run_one(self, schedule: ReportSchedule, now: datetime) -> ReportScheduleRunLog:
        """Sinh + kết xuất + gửi email cho đúng 1 lịch, ghi log, rồi cập
        nhật `last_run_at` — dùng bởi cả `run_due()` (bước tác vụ định kỳ)
        và `run_now()` (chạy thử thủ công, vd cho endpoint API/test)."""
        try:
            recipients = self._recipients.list_for_schedule(schedule.id)
            if not recipients:
                raise NoReportScheduleRecipients(schedule.id)
            to_emails = [r.email for r in recipients]

            report = self._report_generation.generate(
                template_id=schedule.template_id,
                user_id=schedule.user_id,
                year=schedule.year,
                period_type=schedule.period_type,
                period_value=schedule.period_value,
                org_unit_code=schedule.org_unit_code,
                sector=schedule.sector,
            )

            if schedule.format == "EXCEL":
                file_bytes = self._excel_generator.generate(
                    report.template, report.filters, report.rows
                )
                extension, mime_type = (
                    "xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                file_bytes = self._pdf_generator.generate(
                    report.template, report.filters, report.rows
                )
                extension, mime_type = "pdf", "application/pdf"

            filename = f"{report.template.code}-{report.filters.year}.{extension}"
            self._email_sender.send_report_email(
                to_emails=to_emails,
                subject=_email_subject(schedule),
                body_text=_email_body(schedule, report.row_count, report.filters),
                attachment_filename=filename,
                attachment_bytes=file_bytes,
                attachment_mime_type=mime_type,
            )

            log = ReportScheduleRunLog(
                id=None,
                schedule_id=schedule.id,
                status="SUCCESS",
                recipients_count=len(to_emails),
                row_count=report.row_count,
                message="Đã sinh + gửi email báo cáo thành công",
                run_at=now,
            )
        except (DomainError, ReportEmailSendFailed) as exc:
            log = ReportScheduleRunLog(
                id=None,
                schedule_id=schedule.id,
                status="FAILED",
                recipients_count=0,
                row_count=0,
                message=str(exc),
                run_at=now,
            )

        schedule.mark_run(now)
        self._schedules.update(schedule)
        return self._run_logs.add(log)

    def run_now(self, schedule_id: int) -> ReportScheduleRunLog:
        """Chạy thử thủ công 1 lịch ngay lập tức, bỏ qua kiểm tra tới
        hạn — dùng cho endpoint "chạy thử" hoặc test, không thay thế cho
        tác vụ định kỳ (cron) thật ở `run_due()`."""
        schedule = self._schedules.get_by_id(schedule_id)
        if schedule is None:
            from app.domain.exceptions import ReportScheduleNotFound

            raise ReportScheduleNotFound(schedule_id)
        return self._run_one(schedule, datetime.now(timezone.utc))

    def run_due(self, now: Optional[datetime] = None) -> List[ReportScheduleRunLog]:
        """Tác vụ định kỳ (cron): quét toàn bộ lịch đang bật, tới hạn,
        rồi sinh + gửi email báo cáo theo lịch cho từng lịch đó."""
        now = now or datetime.now(timezone.utc)
        logs: List[ReportScheduleRunLog] = []
        for schedule in self._schedules.list_active():
            if _is_due(schedule, now):
                logs.append(self._run_one(schedule, now))
        return logs