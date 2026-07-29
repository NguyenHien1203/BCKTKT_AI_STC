from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.connector_router import router as connector_router
from app.interfaces.api.credential_asset_router import router as credential_asset_router
from app.interfaces.api.data_source_router import router as data_source_router
from app.interfaces.api.source_connection_router import router as source_connection_router

# Import models để Base.metadata biết bảng khi create_all (chỉ dùng cho dev/test
# nhanh bằng SQLite; môi trường Postgres thật dùng Alembic migration).
from app.infrastructure.db import models  # noqa: F401

app = FastAPI(
    title="ingestion-service",
    description="Service phụ trách nhóm UC II. Tiếp nhận và đồng bộ dữ liệu (UC-015 .. UC-028).",
    version="0.1.0",
)

app.include_router(data_source_router)
app.include_router(connector_router)
app.include_router(source_connection_router)
app.include_router(credential_asset_router)


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
    return {"status": "ok", "service": "ingestion-service"}

# UC tiếp theo của service này (UC-018..028): xem PLAN.md, thêm router theo
# mẫu data_source_router.py / connector_router.py / source_connection_router.py
# ở trên và SKILL.md mục A.