import os

import json
import os

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
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


class RoleModel(Base):
    """UC-05: Quản lý vai trò người dùng."""

    __tablename__ = "roles"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    permissions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list[str]
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UserPermissionContextModel(Base):
    """UC-04: Quản lý quyền người dùng."""

    __tablename__ = "user_permission_contexts"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}users.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    permitted_domains: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list[str]
    permitted_unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensitivity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERNAL")


class SystemConfigModel(Base):
    """UC-06: Quản lý cấu hình hệ thống chung — bản ghi singleton (luôn id=1)."""

    __tablename__ = "system_configs"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    default_language: Mapped[str] = mapped_column(String(10), nullable=False, default="vi")
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default="")


class IntegrationEndpointModel(Base):
    """UC-07: Quản lý cấu hình tích hợp — 1 dòng / loại điểm cuối (KEYCLOAK, LGSP)."""

    __tablename__ = "integration_endpoints"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint_type: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    extra_config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    is_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_checked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_check_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class NotificationChannelModel(Base):
    """UC-08: Quản lý cấu hình kênh thông báo — 1 dòng / loại kênh (SMTP, SMS, WEBHOOK)."""

    __tablename__ = "notification_channels"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_type: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_test_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_test_message: Mapped[str] = mapped_column(Text, nullable=False, default="")