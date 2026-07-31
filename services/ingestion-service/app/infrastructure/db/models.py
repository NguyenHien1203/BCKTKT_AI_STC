import os

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base

# Schema "staging" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test.
#
# Lưu ý UC-018: tài liệu nghiệp vụ gốc (BCKTKT) mô tả lưu vào
# "metadata.dataset_catalog" / "metadata.critical_fields", nhưng theo
# ADR-001 (ARCHITECTURE.md mục 7) mỗi service chỉ dùng 1 schema Postgres
# duy nhất — với ingestion-service là `staging`. Vì vậy các bảng
# `dataset_catalog`, `critical_fields`, `dataset_schema_versions` vẫn được
# đặt tên đúng như yêu cầu nghiệp vụ nhưng nằm trong schema `staging` (nhất
# quán với `sources`, `connectors`, `source_connections`).
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

class DatasetModel(Base):
    """UC-018 bước 1-2: Định nghĩa tập dữ liệu + lược đồ, khoá chính +
    chiến lược phân mảnh. Tên bảng theo yêu cầu nghiệp vụ: `dataset_catalog`
    (xem ghi chú schema ở đầu file)."""

    __tablename__ = "dataset_catalog"
    __table_args__ = (
        UniqueConstraint("data_source_id", "code", name="uq_dataset_catalog_source_code"),
        _table_args,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}sources.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    schema_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    primary_key: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    partition_strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")
    partition_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CriticalFieldModel(Base):
    """UC-018 bước 3: Khai báo trường bắt buộc (NOT NULL). Tên bảng theo
    yêu cầu nghiệp vụ: `critical_fields`."""

    __tablename__ = "critical_fields"
    __table_args__ = (
        UniqueConstraint("dataset_id", "field_name", name="uq_critical_fields_dataset_field"),
        _table_args,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)


class SchemaVersionModel(Base):
    """UC-018 bước 4: Đăng ký vào Schema Registry — hệ thống quản lý phiên
    bản lược đồ."""

    __tablename__ = "dataset_schema_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_schema_versions_dataset_version"),
        _table_args,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    registered_at: Mapped[str] = mapped_column(String(40), nullable=False)


class SchemaRegistryCheckModel(Base):
    """UC-026: Kiểm tra Schema Registry — 1 lượt đối chiếu lược đồ nguồn
    (trước khi phân tích) so với lược đồ đã đăng ký gần nhất."""

    __tablename__ = "schema_registry_checks"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    registered_version: Mapped[int] = mapped_column(Integer, nullable=False)
    incoming_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    added_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    removed_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    changed_type_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checked_at: Mapped[str] = mapped_column(String(40), nullable=False)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}ingestion_runs.id"), nullable=True, index=True
    )


class ScheduledTaskModel(Base):
    """UC-019: Cấu hình tác vụ điều phối (lịch cron, đầy đủ/tăng dần,
    chính sách thử lại; bật/tắt; hệ thống cập nhật trạng thái)."""

    __tablename__ = "scheduled_tasks"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL")
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False, default="0 0 * * *")
    retry_max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    retry_backoff: Mapped[str] = mapped_column(String(20), nullable=False, default="FIXED")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IDLE")
    last_run_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_run_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class IngestionRunModel(Base):
    """UC-020: Xem lịch đầy đủ dữ liệu + lịch sử chạy. Tên bảng theo yêu
    cầu nghiệp vụ: "ingestion.runs" — đặt là `ingestion_runs` trong schema
    `staging` (xem ghi chú ADR-001 ở đầu file, nhất quán với các bảng
    khác của ingestion-service)."""

    __tablename__ = "ingestion_runs"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    scheduled_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}scheduled_tasks.id"), nullable=True, index=True
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING", index=True)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    records_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_loaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    control_totals: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    log_entries: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    retry_of_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}ingestion_runs.id"), nullable=True, index=True
    )  # UC-021: Chạy lại phiên ingest lỗi


class TabmisIntakeSessionModel(Base):
    """UC-022: Tiếp nhận file thủ công TABMIS (upload) — 1 phiên tiếp nhận
    ứng với 1 lần tải tệp Excel lên, gắn với 1 bản ghi `ingestion_runs`
    (`ingestion_run_id`)."""

    __tablename__ = "tabmis_intake_sessions"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}dataset_catalog.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RECEIVED", index=True)
    control_totals: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    uploaded_at: Mapped[str] = mapped_column(String(40), nullable=False)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}ingestion_runs.id"), nullable=True, index=True
    )


class TabmisIntakeRowErrorModel(Base):
    """UC-023: Xem trạng thái + sửa lỗi intake TABMIS — các dòng dữ liệu
    sai của 1 phiên tiếp nhận (`tabmis_intake_sessions`)."""

    __tablename__ = "tabmis_intake_row_errors"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}tabmis_intake_sessions.id"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class VanBanIntakeModel(Base):
    """UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (upload định kỳ) — 1
    văn bản tiếp nhận, lưu vào `staging.stg_van_ban`."""

    __tablename__ = "stg_van_ban"
    __table_args__ = _table_args

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_fk_prefix}sources.id"), nullable=False, index=True
    )
    so_ky_hieu: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    loai_van_ban: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    trich_yeu: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ngay_ban_hanh: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    don_vi_ban_hanh: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    raw_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RECEIVED", index=True)
    ocr_event_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    uploaded_at: Mapped[str] = mapped_column(String(40), nullable=False)