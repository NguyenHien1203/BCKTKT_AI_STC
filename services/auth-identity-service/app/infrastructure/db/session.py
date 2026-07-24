import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Ưu tiên biến môi trường DATABASE_URL (Postgres khi deploy thật).
# Fallback SQLite để chạy unit/integration test nhanh không cần hạ tầng.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./auth_identity_dev.db",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
