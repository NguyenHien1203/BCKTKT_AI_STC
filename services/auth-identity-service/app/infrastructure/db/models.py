import os

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base

# Schema "identity" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test.
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_identity_dev.db")
_SCHEMA = "identity" if not _DATABASE_URL.startswith("sqlite") else None

_table_args = {"schema": _SCHEMA} if _SCHEMA else {}


class OrgUnitModel(Base):
    __tablename__ = "org_units"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}org_units.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    org_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}org_units.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="STAFF")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserSessionModel(Base):
    __tablename__ = "user_sessions"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}users.id"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class OrgUnitAssignmentHistoryModel(Base):
    __tablename__ = "org_unit_assignment_history"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}users.id"),
        nullable=False,
        index=True,
    )
    old_org_unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_org_unit_id: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_at: Mapped[str] = mapped_column(String(40), nullable=False)
