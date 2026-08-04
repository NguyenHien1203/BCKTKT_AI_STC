from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.asset_group_catalog_router import router as asset_group_catalog_router
from app.interfaces.api.budget_item_catalog_router import router as budget_item_catalog_router
from app.interfaces.api.mapping_job_router import router as mapping_job_router
from app.interfaces.api.mapping_rule_router import router as mapping_rule_router
from app.interfaces.api.ocr_job_router import router as ocr_job_router
from app.interfaces.api.org_unit_catalog_router import router as org_unit_catalog_router
from app.interfaces.api.parsing_job_router import router as parsing_job_router
from app.interfaces.api.unmapped_queue_router import router as unmapped_queue_router

# Import models để Base.metadata biết bảng khi create_all (chỉ dùng cho dev/test
# nhanh bằng SQLite; môi trường Postgres thật dùng Alembic migration).
from app.infrastructure.db import models  # noqa: F401

app = FastAPI(
    title="data-quality-service",
    description="Service phụ trách nhóm UC III. Chuẩn hóa và quản trị dữ liệu (UC-029 .. UC-046).",
    version="0.2.0",
)

app.include_router(parsing_job_router)
app.include_router(ocr_job_router)
app.include_router(mapping_rule_router)
app.include_router(mapping_job_router)
app.include_router(unmapped_queue_router)
app.include_router(org_unit_catalog_router)
app.include_router(budget_item_catalog_router)
app.include_router(asset_group_catalog_router)


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
    return {"status": "ok", "service": "data-quality-service"}