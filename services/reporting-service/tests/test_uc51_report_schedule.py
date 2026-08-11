"""Integration test UC-051 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REPORT_SCHEDULER_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.report_email_sender import _noop_singleton  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

_SAMPLE_COLUMNS = [
    {"field": "don_vi", "label": "Đơn vị", "data_type": "STRING"},
    {"field": "gia_tri", "label": "Giá trị", "data_type": "DECIMAL"},
]


def _register_template(code="RPT-UC51-01", available_periods=None):
    resp = client.post(
        "/report-templates",
        json={
            "code": code,
            "name": "Báo cáo demo UC-051",
            "description": "Mẫu báo cáo demo cho test UC-051",
            "category": "NGAN_SACH",
            "columns": _SAMPLE_COLUMNS,
            "available_periods": available_periods or ["THANG", "QUY", "NAM"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_schedule(template_id, user_id=1, **overrides):
    payload = {
        "user_id": user_id,
        "frequency": "DAILY",
        "time_of_day": "07:00",
        "format": "PDF",
        "year": 2026,
        "period_type": "NAM",
    }
    payload.update(overrides)
    resp = client.post(f"/report-templates/{template_id}/schedules", json=payload)
    return resp


def test_configure_daily_schedule_returns_saved_schedule():
    template = _register_template(code="RPT-UC51-DAILY")
    resp = _create_schedule(template["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["template_id"] == template["id"]
    assert body["frequency"] == "DAILY"
    assert body["time_of_day"] == "07:00"
    assert body["format"] == "PDF"
    assert body["is_active"] is True
    assert body["last_run_at"] is None


def test_configure_weekly_schedule_requires_day_of_week():
    template = _register_template(code="RPT-UC51-WEEKLY-MISSING")
    resp = _create_schedule(template["id"], frequency="WEEKLY")
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_REPORT_SCHEDULE"


def test_configure_weekly_schedule_with_day_of_week_ok():
    template = _register_template(code="RPT-UC51-WEEKLY-OK")
    resp = _create_schedule(template["id"], frequency="WEEKLY", day_of_week=1)
    assert resp.status_code == 201, resp.text
    assert resp.json()["day_of_week"] == 1


def test_configure_monthly_schedule_requires_day_of_month():
    template = _register_template(code="RPT-UC51-MONTHLY-MISSING")
    resp = _create_schedule(template["id"], frequency="MONTHLY")
    assert resp.status_code == 422, resp.text


def test_configure_monthly_schedule_day_of_month_over_28_rejected():
    template = _register_template(code="RPT-UC51-MONTHLY-OVER28")
    resp = _create_schedule(template["id"], frequency="MONTHLY", day_of_month=30)
    assert resp.status_code == 422, resp.text


def test_configure_schedule_invalid_time_of_day_rejected():
    template = _register_template(code="RPT-UC51-BADTIME")
    resp = client.post(
        f"/report-templates/{template['id']}/schedules",
        json={"user_id": 1, "frequency": "DAILY", "time_of_day": "25:99"},
    )
    assert resp.status_code == 422, resp.text


def test_configure_schedule_template_not_found_returns_404():
    resp = _create_schedule(999999)
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_NOT_FOUND"


def test_list_schedules_for_user():
    template = _register_template(code="RPT-UC51-LIST")
    _create_schedule(template["id"], user_id=5)
    _create_schedule(template["id"], user_id=5, frequency="WEEKLY", day_of_week=2)
    resp = client.get(f"/report-templates/{template['id']}/schedules", params={"user_id": 5})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


def test_update_schedule_config():
    template = _register_template(code="RPT-UC51-UPDATE")
    created = _create_schedule(template["id"]).json()
    resp = client.put(
        f"/report-templates/{template['id']}/schedules/{created['id']}",
        json={
            "frequency": "WEEKLY",
            "time_of_day": "08:30",
            "format": "EXCEL",
            "day_of_week": 3,
            "year": 2026,
            "period_type": "NAM",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["frequency"] == "WEEKLY"
    assert body["time_of_day"] == "08:30"
    assert body["format"] == "EXCEL"
    assert body["day_of_week"] == 3


def test_enable_disable_schedule():
    template = _register_template(code="RPT-UC51-ENABLE")
    created = _create_schedule(template["id"]).json()
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/disable")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/enable")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_add_recipient_and_list():
    template = _register_template(code="RPT-UC51-RECIPIENTS")
    created = _create_schedule(template["id"]).json()
    resp = client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "cbo1@stc.gov.vn"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["email"] == "cbo1@stc.gov.vn"

    resp = client.get(f"/report-templates/{template['id']}/schedules/{created['id']}/recipients")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_add_duplicate_recipient_returns_409():
    template = _register_template(code="RPT-UC51-DUP")
    created = _create_schedule(template["id"]).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "dup@stc.gov.vn"},
    )
    resp = client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "dup@stc.gov.vn"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "REPORT_SCHEDULE_RECIPIENT_EXISTS"


def test_add_invalid_email_returns_422():
    template = _register_template(code="RPT-UC51-BADEMAIL")
    created = _create_schedule(template["id"]).json()
    resp = client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "not-an-email"},
    )
    assert resp.status_code == 422, resp.text


def test_remove_recipient():
    template = _register_template(code="RPT-UC51-REMOVE")
    created = _create_schedule(template["id"]).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "remove-me@stc.gov.vn"},
    )
    resp = client.delete(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients/remove-me@stc.gov.vn"
    )
    assert resp.status_code == 204, resp.text
    resp = client.get(f"/report-templates/{template['id']}/schedules/{created['id']}/recipients")
    assert resp.json() == []


def test_remove_recipient_not_found_returns_404():
    template = _register_template(code="RPT-UC51-REMOVE-404")
    created = _create_schedule(template["id"]).json()
    resp = client.delete(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients/none@stc.gov.vn"
    )
    assert resp.status_code == 404, resp.text


def test_run_now_without_recipients_records_failed_log():
    template = _register_template(code="RPT-UC51-RUNNOW-NORECIPIENT")
    created = _create_schedule(template["id"]).json()
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["recipients_count"] == 0


def test_run_now_with_recipients_sends_email_and_records_success_log():
    _noop_singleton.sent_emails.clear()
    template = _register_template(code="RPT-UC51-RUNNOW-OK")
    created = _create_schedule(template["id"], format="PDF").json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "a@stc.gov.vn"},
    )
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "b@stc.gov.vn"},
    )

    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SUCCESS"
    assert body["recipients_count"] == 2
    assert body["row_count"] > 0

    assert len(_noop_singleton.sent_emails) == 1
    sent = _noop_singleton.sent_emails[0]
    assert set(sent.to_emails) == {"a@stc.gov.vn", "b@stc.gov.vn"}
    assert sent.attachment_filename.endswith(".pdf")

    # last_run_at đã được cập nhật sau khi chạy
    resp = client.get(f"/report-templates/{template['id']}/schedules/{created['id']}")
    assert resp.json()["last_run_at"] is not None


def test_run_now_excel_format_sends_xlsx_attachment():
    _noop_singleton.sent_emails.clear()
    template = _register_template(code="RPT-UC51-RUNNOW-EXCEL")
    created = _create_schedule(template["id"], format="EXCEL").json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "c@stc.gov.vn"},
    )
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUCCESS"
    assert _noop_singleton.sent_emails[-1].attachment_filename.endswith(".xlsx")


def test_run_now_uses_saved_filter_config_when_schedule_has_no_filters():
    template = _register_template(code="RPT-UC51-RUNNOW-SAVEDFILTER")
    client.put(
        f"/report-templates/{template['id']}/filter-config",
        json={"user_id": 7, "year": 2025, "period_type": "QUY", "period_value": 3},
    )
    created = _create_schedule(
        template["id"], user_id=7, year=None, period_type=None
    ).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "d@stc.gov.vn"},
    )
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUCCESS"


def test_run_now_without_saved_filter_and_no_direct_filter_fails_gracefully():
    template = _register_template(code="RPT-UC51-RUNNOW-NOFILTER")
    created = _create_schedule(
        template["id"], user_id=99, year=None, period_type=None
    ).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "e@stc.gov.vn"},
    )
    resp = client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "bộ lọc" in body["message"].lower() or "filter" in body["message"].lower()


def test_run_now_schedule_not_found_returns_404():
    template = _register_template(code="RPT-UC51-RUNNOW-404")
    resp = client.post(f"/report-templates/{template['id']}/schedules/999999/run-now")
    assert resp.status_code == 404, resp.text


def test_list_run_logs_returns_history():
    template = _register_template(code="RPT-UC51-LOGS")
    created = _create_schedule(template["id"]).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{created['id']}/recipients",
        json={"email": "f@stc.gov.vn"},
    )
    client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")
    client.post(f"/report-templates/{template['id']}/schedules/{created['id']}/run-now")

    resp = client.get(f"/report-templates/{template['id']}/schedules/{created['id']}/logs")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


def test_is_due_logic_for_run_due_scan():
    """Kiểm tra trực tiếp hàm `_is_due` (không qua HTTP) cho cả 3 tần suất
    — đảm bảo tác vụ định kỳ (cron) chỉ chạy đúng lịch tới hạn."""
    from datetime import datetime, timezone

    from app.application.use_cases.run_scheduled_reports import _is_due
    from app.domain.entities import ReportSchedule

    daily = ReportSchedule(
        id=1, template_id=1, user_id=1, frequency="DAILY", time_of_day="07:00"
    )
    before = datetime(2026, 8, 11, 6, 0, tzinfo=timezone.utc)
    after = datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc)
    assert _is_due(daily, before) is False
    assert _is_due(daily, after) is True

    daily.last_run_at = datetime(2026, 8, 11, 7, 5, tzinfo=timezone.utc)
    assert _is_due(daily, datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)) is False
    assert _is_due(daily, datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)) is True

    weekly = ReportSchedule(
        id=2,
        template_id=1,
        user_id=1,
        frequency="WEEKLY",
        time_of_day="09:00",
        day_of_week=2,
    )
    wrong_day = datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)  # thứ Ba = weekday 1
    right_day = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)  # thứ Tư = weekday 2
    assert _is_due(weekly, wrong_day) is False
    assert _is_due(weekly, right_day) is True

    monthly = ReportSchedule(
        id=3,
        template_id=1,
        user_id=1,
        frequency="MONTHLY",
        time_of_day="09:00",
        day_of_month=15,
    )
    assert _is_due(monthly, datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc)) is False
    assert _is_due(monthly, datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)) is True


def test_run_due_scans_and_runs_only_due_active_schedules():
    """Test bước 3 (tác vụ định kỳ/cron) ở tầng application, gọi thẳng
    `ReportScheduleRunnerService.run_due()` với `now` giả lập — không phụ
    thuộc APScheduler thật (APScheduler tắt trong test, xem
    `REPORT_SCHEDULER_ENABLED=false` ở đầu file)."""
    from datetime import datetime, timezone

    from app.application.use_cases.generate_and_export_report import ReportGenerationService
    from app.application.use_cases.run_scheduled_reports import ReportScheduleRunnerService
    from app.infrastructure.db.repository_impl import (
        SqlAlchemyGeneratedReportLogRepository,
        SqlAlchemyReportFilterConfigRepository,
        SqlAlchemyReportScheduleRecipientRepository,
        SqlAlchemyReportScheduleRepository,
        SqlAlchemyReportScheduleRunLogRepository,
        SqlAlchemyReportTemplateRepository,
    )
    from app.infrastructure.db.session import SessionLocal
    from app.infrastructure.report_email_sender import NoOpReportEmailSender
    from app.infrastructure.semantic_layer_report_client import (
        get_semantic_layer_report_query_client,
    )

    template = _register_template(code="RPT-UC51-RUNDUE")
    due_schedule = _create_schedule(
        template["id"], user_id=11, frequency="DAILY", time_of_day="00:00"
    ).json()
    not_due_schedule = _create_schedule(
        template["id"], user_id=11, frequency="DAILY", time_of_day="23:59"
    ).json()
    client.post(
        f"/report-templates/{template['id']}/schedules/{due_schedule['id']}/recipients",
        json={"email": "g@stc.gov.vn"},
    )
    client.post(
        f"/report-templates/{template['id']}/schedules/{not_due_schedule['id']}/recipients",
        json={"email": "h@stc.gov.vn"},
    )

    db = SessionLocal()
    try:
        test_email_sender = NoOpReportEmailSender()
        runner = ReportScheduleRunnerService(
            schedule_repo=SqlAlchemyReportScheduleRepository(db),
            recipient_repo=SqlAlchemyReportScheduleRecipientRepository(db),
            run_log_repo=SqlAlchemyReportScheduleRunLogRepository(db),
            report_generation_service=ReportGenerationService(
                template_repo=SqlAlchemyReportTemplateRepository(db),
                filter_config_repo=SqlAlchemyReportFilterConfigRepository(db),
                query_client=get_semantic_layer_report_query_client(),
                log_repo=SqlAlchemyGeneratedReportLogRepository(db),
            ),
            email_sender=test_email_sender,
        )
        now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
        logs = runner.run_due(now=now)
    finally:
        db.close()

    assert any(log.schedule_id == due_schedule["id"] and log.status == "SUCCESS" for log in logs)
    assert all(log.schedule_id != not_due_schedule["id"] for log in logs)
    assert len(test_email_sender.sent_emails) >= 1