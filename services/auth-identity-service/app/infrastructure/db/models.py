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


class AuditLogModel(Base):
    """UC-09: Quản lý nhật ký truy cập và thao tác — append-only."""

    __tablename__ = "audit_logs"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)


class AiAuditLogModel(Base):
    """UC-10: Quản trị AI Audit Log — append-only, mỗi dòng 1 phiên hỏi-đáp AI."""

    __tablename__ = "ai_audit_logs"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sources: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list[str]
    permission_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)


class GuideDocumentModel(Base):
    """UC-11: Quản trị tài liệu hướng dẫn sử dụng — tệp thực tế lưu ở MinIO,
    dòng này chỉ lưu siêu dữ liệu + `file_key` trỏ tới đối tượng MinIO."""

    __tablename__ = "guide_documents"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


class GuideDocumentVersionModel(Base):
    """UC-11: lịch sử phiên bản tài liệu hướng dẫn — append-only."""

    __tablename__ = "guide_document_versions"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}guide_documents.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)


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