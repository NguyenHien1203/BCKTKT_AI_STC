import os

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base

# Schema "staging" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test.
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ingestion_service_dev.db")
_SCHEMA = "staging" if not _DATABASE_URL.startswith("sqlite") else None

_table_args = {"schema": _SCHEMA} if _SCHEMA else {}
_fk_prefix = f"{_SCHEMA}." if _SCHEMA else ""


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


class ConnectorModel(Base):
    """UC-016: Quản lý thư viện bộ kết nối."""

    __tablename__ = "connectors"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_point: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    interface_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PASSED")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    restart_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SourceConnectionModel(Base):
    """UC-017: Cấu hình kết nối nguồn (credentials/cert)."""

    __tablename__ = "source_connections"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}sources.id"), nullable=False, index=True
    )
    connection_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_test_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNTESTED")
    last_test_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_tested_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CredentialAssetModel(Base):
    """UC-017: Certificate/API key của bộ kết nối + lịch luân chuyển."""

    __tablename__ = "credential_assets"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_fk_prefix}source_connections.id"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[str] = mapped_column(String(40), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    rotation_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    rotated_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rotation_history: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)