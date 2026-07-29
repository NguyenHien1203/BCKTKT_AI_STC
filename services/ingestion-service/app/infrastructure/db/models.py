import os

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base

# Schema "staging" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test.
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ingestion_service_dev.db")
_SCHEMA = "staging" if not _DATABASE_URL.startswith("sqlite") else None

_table_args = {"schema": _SCHEMA} if _SCHEMA else {}


class DataSourceModel(Base):
    """UC-015: Đăng ký và quản lý nguồn dữ liệu."""

    __tablename__ = "sources"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    owner: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sensitivity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERNAL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
