from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.dashboard_router import router as dashboard_router
from app.interfaces.api.kpi_query_router import router as kpi_query_router
from app.interfaces.api.report_template_router import router as report_template_router

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


@app.get("/health")
def health():
    return {"status": "ok", "service": "reporting-service"}

# UC tiếp theo của service này (UC-048..057): xem PLAN.md, thêm router theo
# mẫu dashboard_router.py ở trên và SKILL.md mục A.