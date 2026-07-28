from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.ai_audit_log_router import router as ai_audit_log_router
from app.interfaces.api.audit_log_router import router as audit_log_router
from app.interfaces.api.auth_router import router as auth_router
from app.interfaces.api.guide_document_router import router as guide_document_router
from app.interfaces.api.integration_config_router import router as integration_config_router
from app.interfaces.api.notification_channel_router import router as notification_channel_router
from app.interfaces.api.org_unit_router import router as org_unit_router
from app.interfaces.api.permission_router import router as permission_router
from app.interfaces.api.role_router import router as role_router
from app.interfaces.api.system_config_router import router as system_config_router
from app.interfaces.api.user_router import lifecycle_router, router as user_router

# Import models để Base.metadata biết bảng khi create_all (chỉ dùng cho dev/test
# nhanh bằng SQLite; môi trường Postgres thật dùng Alembic migration).
from app.infrastructure.db import models  # noqa: F401

app = FastAPI(
    title="auth-identity-service",
    description=(
        "Service phụ trách nhóm UC I. Quản trị hệ thống "
        "(UC-01 .. UC-14) — Kho dữ liệu tổng hợp ngành Tài chính "
        "tỉnh Hưng Yên."
    ),
    version="0.1.0",
)

app.include_router(org_unit_router)
app.include_router(user_router)
app.include_router(lifecycle_router)
app.include_router(auth_router)
app.include_router(role_router)
app.include_router(permission_router)
app.include_router(system_config_router)
app.include_router(integration_config_router)
app.include_router(notification_channel_router)
app.include_router(audit_log_router)
app.include_router(ai_audit_log_router)
app.include_router(guide_document_router)


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
    return {"status": "ok", "service": "auth-identity-service"}