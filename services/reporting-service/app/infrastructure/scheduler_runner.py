"""Infrastructure — UC-051 bước cuối: "Tác vụ định kỳ (cron)".

Dùng `APScheduler` (`BackgroundScheduler`) chạy 1 job nội bộ mỗi phút,
quét các lịch báo cáo đang bật + tới hạn (`ReportScheduleRunnerService
.run_due()`) rồi tự sinh + gửi email — đúng tinh thần "tác vụ định kỳ
(cron)" nhưng chạy ngay trong tiến trình `reporting-service` (không cần
thêm service/cron riêng ở tầng hạ tầng, phù hợp quy mô hệ thống hiện tại;
`ingestion-service` UC-019 chỉ LƯU cấu hình cron cho Bộ điều phối ngoài,
còn ở đây UC-051 cần "tự động" chạy nên chọn chạy cron nội bộ).

Chỉ khởi động khi biến môi trường `REPORT_SCHEDULER_ENABLED=true` (mặc
định TẮT) — tránh chạy nền ngoài ý muốn khi chạy `pytest`/dev nhanh bằng
SQLite (mỗi test tạo `TestClient(app)` riêng, không nên có thread nền).
"""
import logging
import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

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
from app.infrastructure.report_email_sender import get_report_email_sender
from app.infrastructure.semantic_layer_report_client import (
    get_semantic_layer_report_query_client,
)

logger = logging.getLogger("reporting-service.scheduler")

_scheduler: Optional[BackgroundScheduler] = None

SCHEDULER_ENABLED = os.getenv("REPORT_SCHEDULER_ENABLED", "false").lower() == "true"
# Cron nội bộ quét mỗi phút — đủ nhỏ để không trễ quá 1 phút so với
# `time_of_day` cấu hình, không cần chính xác tới giây cho báo cáo định kỳ.
POLL_INTERVAL_SECONDS = int(os.getenv("REPORT_SCHEDULER_POLL_SECONDS", "60"))


def run_due_schedules_once() -> None:
    """Mở 1 phiên DB riêng, quét + chạy các lịch tới hạn, rồi đóng phiên
    — gọi bởi job APScheduler (tác vụ định kỳ), tách biệt khỏi phiên DB
    theo từng request HTTP."""
    db = SessionLocal()
    try:
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
            email_sender=get_report_email_sender(),
        )
        logs = runner.run_due()
        if logs:
            logger.info("Tác vụ định kỳ (UC-051) đã chạy %d lịch báo cáo", len(logs))
    except Exception:  # pragma: no cover - phòng lỗi hạ tầng, không để job chết hẳn
        logger.exception("Tác vụ định kỳ (UC-051) gặp lỗi khi quét lịch báo cáo")
    finally:
        db.close()


def start_background_scheduler() -> Optional[BackgroundScheduler]:
    """Khởi động job cron nội bộ nếu `REPORT_SCHEDULER_ENABLED=true`.
    Gọi 1 lần ở `app.main` khi FastAPI khởi động (startup event)."""
    global _scheduler
    if not SCHEDULER_ENABLED:
        logger.info(
            "REPORT_SCHEDULER_ENABLED=false — không khởi động tác vụ định kỳ (UC-051)"
        )
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_due_schedules_once,
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="uc051_run_due_report_schedules",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Đã khởi động tác vụ định kỳ (UC-051), quét mỗi %ds", POLL_INTERVAL_SECONDS
    )
    return _scheduler


def stop_background_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None