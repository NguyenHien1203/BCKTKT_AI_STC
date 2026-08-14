"""SQLAlchemy models cho api-gateway-service."""
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
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