import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

# Ưu tiên biến môi trường DATABASE_URL (Postgres khi deploy thật).
# Fallback SQLite để chạy unit/integration test nhanh không cần hạ tầng.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./auth_identity_dev.db",
)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_sqlite_memory = DATABASE_URL in ("sqlite:///:memory:", "sqlite://")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# SQLite `:memory:` tạo 1 DB riêng biệt cho mỗi connection theo mặc định
# (QueuePool) — dẫn tới lỗi "no such table" khi request thứ 2 mở connection
# mới. StaticPool giữ đúng 1 connection dùng chung cho toàn bộ engine, cần
# thiết khi chạy test với SQLite in-memory.
engine_kwargs = {"connect_args": connect_args, "future": True}
if _is_sqlite_memory:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()