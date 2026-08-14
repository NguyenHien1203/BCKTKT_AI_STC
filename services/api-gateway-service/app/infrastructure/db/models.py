"""SQLAlchemy models cho api-gateway-service."""
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import SCHEMA, Base, engine


def _schema_kwargs() -> dict:
    # SQLite (dev/test) không hỗ trợ schema Postgres -> bỏ qua khi dev/test.
    if engine.url.get_backend_name() == "sqlite":
        return {}
    return {"schema": SCHEMA}


class ApiCatalogEntryModel(Base):
    __tablename__ = "api_catalog_entries"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    api_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    endpoint_path: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PUBLISHED", index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sunset_date: Mapped[Date] = mapped_column(Date, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    unpublished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ApiCatalogVersionHistoryModel(Base):
    __tablename__ = "api_catalog_version_history"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            f"{SCHEMA}.api_catalog_entries.id"
            if engine.url.get_backend_name() != "sqlite"
            else "api_catalog_entries.id"
        ),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    sunset_date: Mapped[Date] = mapped_column(Date, nullable=True)
    change_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


def _fk(table_col: str) -> str:
    """FK phải trỏ đúng schema khi chạy Postgres, bỏ schema khi SQLite.

    `table_col` có dạng "table.column" (không kèm schema).
    """
    if engine.url.get_backend_name() == "sqlite":
        return table_col
    return f"{SCHEMA}.{table_col}"


class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    consumer_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(500), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    rotated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    grace_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    previous_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_fk("api_keys.id")), nullable=True
    )
    rotated_to_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_fk("api_keys.id")), nullable=True
    )


class ApiKeyUsageLogModel(Base):
    __tablename__ = "api_key_usage_logs"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_fk("api_keys.id")), nullable=False, index=True
    )
    endpoint_path: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    consumer_ip: Mapped[str] = mapped_column(String(64), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    called_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

class ServiceTierModel(Base):
    __tablename__ = "service_tiers"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class RateLimitPolicyModel(Base):
    __tablename__ = "rate_limit_policies"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_fk("service_tiers.id")), nullable=False, unique=True, index=True
    )
    requests_per_second: Mapped[int] = mapped_column(Integer, nullable=False)
    requests_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class BurstPolicyModel(Base):
    __tablename__ = "burst_policies"
    __table_args__ = _schema_kwargs()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_fk("service_tiers.id")), nullable=False, unique=True, index=True
    )
    burst_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    throttle_policy: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)