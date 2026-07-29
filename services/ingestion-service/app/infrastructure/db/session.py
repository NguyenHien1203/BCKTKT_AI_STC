import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ingestion_service_dev.db",
)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_sqlite_memory = DATABASE_URL in ("sqlite:///:memory:", "sqlite://")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

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