import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data_quality_service_dev.db",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# SQLite in-memory (":memory:") tạo 1 CSDL mới cho MỖI lần mở connection
# riêng biệt -- nếu không ghim vào đúng 1 connection (StaticPool), các
# request khác nhau (mỗi request 1 Session/connection qua get_db()) sẽ
# thấy CSDL trống ("no such table"). Bug hạ tầng có sẵn từ trước, phát
# hiện khi chạy pytest cho UC-032 -- chỉ áp dụng cho SQLite in-memory
# dùng trong test; SQLite trên đĩa (dev) và Postgres (production) không
# bị ảnh hưởng vì mỗi connection đều trỏ tới cùng 1 CSDL thật.
engine_kwargs = {"connect_args": connect_args, "future": True}
if DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

SCHEMA = "curated"


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()