"""Application layer — UC-051: Cấu hình báo cáo theo lịch.

Đối chiếu docs/use_cases.json id=51: actor "Cán bộ tổng hợp Sở Tài chính".
Luồng:
  1. Cấu hình lịch (hàng ngày/hàng tuần/hàng tháng) -> hệ thống lưu lịch.
  2. Cấu hình người nhận (email) -> hệ thống lưu.
  3. Hệ thống tự động sinh + gửi email báo cáo theo lịch -> tác vụ định kỳ
     (cron) — xem `app/application/use_cases/run_scheduled_reports.py`.
"""
from typing import List, Optional

from app.domain.entities import ReportSchedule, ReportScheduleRecipient, ReportScheduleRunLog
from app.domain.exceptions import (
    InvalidReportSchedule,
    ReportScheduleNotFound,
    ReportScheduleRecipientAlreadyExists,
    ReportScheduleRecipientNotFound,
    ReportTemplateInactive,
    ReportTemplateNotFound,
)
from app.domain.repositories import (
    ReportScheduleRecipientRepository,
    ReportScheduleRepository,
    ReportScheduleRunLogRepository,
    ReportTemplateRepository,
)


class ReportScheduleService:
    def __init__(
        self,
        schedule_repo: ReportScheduleRepository,
        recipient_repo: ReportScheduleRecipientRepository,
        run_log_repo: ReportScheduleRunLogRepository,
        template_repo: ReportTemplateRepository,
    ):
        self._schedules = schedule_repo
        self._recipients = recipient_repo
        self._run_logs = run_log_repo
        self._templates = template_repo

    # ---------- Bước 1: Cấu hình lịch -> hệ thống lưu lịch ----------

    def configure(
        self,
        template_id: int,
        user_id: int,
        frequency: str,
        time_of_day: str,
        format: str = "PDF",
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        year: Optional[int] = None,
        period_type: Optional[str] = None,
        period_value: Optional[int] = None,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> ReportSchedule:
        template = self._templates.get_by_id(template_id)
        if template is None:
            raise ReportTemplateNotFound(template_id)
        if not template.is_active:
            raise ReportTemplateInactive(template_id)

        try:
            schedule = ReportSchedule(
                id=None,
                template_id=template_id,
                user_id=user_id,
                frequency=frequency,
                time_of_day=time_of_day,
                format=format,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                year=year,
                period_type=period_type,
                period_value=period_value,
                org_unit_code=org_unit_code,
                sector=sector,
            )
        except ValueError as exc:
            raise InvalidReportSchedule(str(exc)) from exc

        return self._schedules.add(schedule)

    def get(self, schedule_id: int) -> ReportSchedule:
        schedule = self._schedules.get_by_id(schedule_id)
        if schedule is None:
            raise ReportScheduleNotFound(schedule_id)
        return schedule

    def list_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[ReportSchedule]:
        return self._schedules.list_for_user(user_id, template_id=template_id)

    def update_config(
        self,
        schedule_id: int,
        frequency: str,
        time_of_day: str,
        format: str = "PDF",
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        year: Optional[int] = None,
        period_type: Optional[str] = None,
        period_value: Optional[int] = None,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> ReportSchedule:
        """Sửa cấu hình lịch đã có: hệ thống lưu."""
        schedule = self.get(schedule_id)
        try:
            updated = ReportSchedule(
                id=schedule.id,
                template_id=schedule.template_id,
                user_id=schedule.user_id,
                frequency=frequency,
                time_of_day=time_of_day,
                format=format,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                year=year,
                period_type=period_type,
                period_value=period_value,
                org_unit_code=org_unit_code,
                sector=sector,
                is_active=schedule.is_active,
                last_run_at=schedule.last_run_at,
                created_at=schedule.created_at,
            )
        except ValueError as exc:
            raise InvalidReportSchedule(str(exc)) from exc
        return self._schedules.update(updated)

    def enable(self, schedule_id: int) -> ReportSchedule:
        schedule = self.get(schedule_id)
        schedule.enable()
        return self._schedules.update(schedule)

    def disable(self, schedule_id: int) -> ReportSchedule:
        schedule = self.get(schedule_id)
        schedule.disable()
        return self._schedules.update(schedule)

    # ---------- Bước 2: Cấu hình người nhận (email) -> hệ thống lưu ----------

    def add_recipient(self, schedule_id: int, email: str) -> ReportScheduleRecipient:
        self.get(schedule_id)  # đảm bảo lịch tồn tại
        email = email.strip()
        if self._recipients.get(schedule_id, email) is not None:
            raise ReportScheduleRecipientAlreadyExists(schedule_id, email)
        try:
            recipient = ReportScheduleRecipient(id=None, schedule_id=schedule_id, email=email)
        except ValueError as exc:
            raise InvalidReportSchedule(str(exc)) from exc
        return self._recipients.add(recipient)

    def remove_recipient(self, schedule_id: int, email: str) -> None:
        self.get(schedule_id)
        deleted = self._recipients.delete(schedule_id, email.strip())
        if not deleted:
            raise ReportScheduleRecipientNotFound(schedule_id, email)

    def list_recipients(self, schedule_id: int) -> List[ReportScheduleRecipient]:
        self.get(schedule_id)
        return self._recipients.list_for_schedule(schedule_id)

    # ---------- Lịch sử chạy tác vụ định kỳ (cron) ----------

    def list_run_logs(self, schedule_id: int) -> List[ReportScheduleRunLog]:
        self.get(schedule_id)
        return self._run_logs.list_for_schedule(schedule_id)