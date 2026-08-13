from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.dashboard_alert_router import router as dashboard_alert_router
from app.interfaces.api.dashboard_alert_router import user_router as dashboard_alert_user_router
from app.interfaces.api.dashboard_router import router as dashboard_router
from app.interfaces.api.document_search_router import router as document_search_router
from app.interfaces.api.kpi_query_router import router as kpi_query_router
from app.interfaces.api.price_data_router import router as price_data_router
from app.interfaces.api.report_generation_router import router as report_generation_router
from app.interfaces.api.report_schedule_router import router as report_schedule_router
from app.interfaces.api.report_template_router import router as report_template_router
from app.infrastructure.scheduler_runner import start_background_scheduler, stop_background_scheduler

# Import models để Base.metadata biết bảng khi create_all (chỉ dùng cho dev/test
# nhanh bằng SQLite; môi trường Postgres thật dùng Alembic migration).
from app.infrastructure.db import models  # noqa: F401

app = FastAPI(
    title="reporting-service",
    description="Service phụ trách nhóm UC IV. Khai thác: Bảng điều khiển và báo cáo (UC-047 .. UC-057).",
    version="0.1.0",
)

app.include_router(dashboard_router)
app.include_router(kpi_query_router)
app.include_router(report_template_router)
app.include_router(report_generation_router)
app.include_router(report_schedule_router)
app.include_router(dashboard_alert_router)
app.include_router(dashboard_alert_user_router)
app.include_router(document_search_router)
app.include_router(price_data_router)


def _create_sqlite_tables_if_needed() -> None:
    # Chỉ tự tạo bảng khi dùng SQLite dev/test; Postgres production dùng Alembic.
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.create_all(bind=engine)


# Tạo bảng ngay khi import app (không chỉ ở startup event) — cần thiết vì
# TestClient(app) dùng trực tiếp (không qua context manager `with`) không
# đảm bảo trigger lifespan/startup event ở mọi phiên bản Starlette.
_create_sqlite_tables_if_needed()


@app.on_event("startup")
def on_startup() -> None:
    _create_sqlite_tables_if_needed()
    # UC-051 — "Tác vụ định kỳ (cron)": chỉ chạy khi REPORT_SCHEDULER_ENABLED=true
    # (mặc định tắt, xem app/infrastructure/scheduler_runner.py).
    start_background_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_background_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "service": "reporting-service"}

# UC tiếp theo của service này (UC-048..057): xem PLAN.md, thêm router theo
# mẫu dashboard_router.py ở trên và SKILL.md mục A.