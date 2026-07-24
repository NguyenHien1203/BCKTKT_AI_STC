from fastapi import FastAPI

from app.infrastructure.db.session import Base, engine
from app.interfaces.api.auth_router import router as auth_router
from app.interfaces.api.org_unit_router import router as org_unit_router
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


@app.on_event("startup")
def on_startup() -> None:
    # Chỉ tự tạo bảng khi dùng SQLite dev; Postgres production dùng Alembic.
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-identity-service"}
