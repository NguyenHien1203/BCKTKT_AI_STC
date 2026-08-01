"""SQLAlchemy models cho data-quality-service — UC-029."""
import os

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.infrastructure.db.session import Base

# Schema "curated" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test
# — cùng pattern với ingestion-service (xem app/infrastructure/db/models.py
# bên đó).
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data_quality_service_dev.db")
_SCHEMA = "curated" if not _DATABASE_URL.startswith("sqlite") else None

_table_args = {"schema": _SCHEMA} if _SCHEMA else {}
_fk_prefix = f"{_SCHEMA}." if _SCHEMA else ""


class ParsingJobModel(Base):
    __tablename__ = "parsing_jobs"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=False, index=True)
    ingestion_run_id = Column(Integer, nullable=True, index=True)
    data_source_id = Column(Integer, nullable=True)
    source_format = Column(String(20), nullable=False)
    raw_object_key = Column(String(500), nullable=False)
    schema_fields_json = Column(Text, nullable=False, default="[]")
    field_mapping_json = Column(Text, nullable=False, default="{}")
    status = Column(String(20), nullable=False, default="RECEIVED", index=True)
    records_read = Column(Integer, nullable=False, default=0)
    records_parsed = Column(Integer, nullable=False, default=0)
    records_failed = Column(Integer, nullable=False, default=0)
    mapping_event_published = Column(Boolean, nullable=False, default=False)
    log_entries_json = Column(Text, nullable=False, default="[]")
    error_message = Column(Text, nullable=True)
    received_at = Column(String(40), nullable=False)
    completed_at = Column(String(40), nullable=True)


class StgStructuredRowModel(Base):
    """Bước 2 'Hệ thống đọc dữ liệu thô -> stg_*': bản sao thô của từng
    dòng/bản ghi đọc được từ nguồn, trước khi ánh xạ + ép kiểu."""

    __tablename__ = "stg_structured_rows"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    parsing_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}parsing_jobs.id"), nullable=False, index=True
    )
    row_index = Column(Integer, nullable=False)
    raw_data_json = Column(Text, nullable=False)


class ParsedStructuredRecordModel(Base):
    """Bước 4 kết quả: bản ghi đã ánh xạ tên trường + ép kiểu, để UC-031
    đọc tiếp sau khi nhận sự kiện `mapping.requested`."""

    __tablename__ = "parsed_structured_records"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    parsing_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}parsing_jobs.id"), nullable=False, index=True
    )
    row_index = Column(Integer, nullable=False)
    mapped_fields_json = Column(Text, nullable=False)
    has_error = Column(Boolean, nullable=False, default=False)


class ParsingRowErrorModel(Base):
    __tablename__ = "parsing_row_errors"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    parsing_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}parsing_jobs.id"), nullable=False, index=True
    )
    row_index = Column(Integer, nullable=False)
    field_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)


class OcrJobModel(Base):
    """UC-030: 1 lượt xử lý OCR (1 sự kiện `ocr.requested` = 1 OcrJob)."""

    __tablename__ = "ocr_jobs"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_intake_id = Column(Integer, nullable=True, index=True)
    data_source_id = Column(Integer, nullable=True)
    so_ky_hieu = Column(String(255), nullable=True)
    raw_object_key = Column(String(500), nullable=False)
    engine_requested = Column(String(20), nullable=False, default="PADDLEOCR")
    engine_used = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="RECEIVED", index=True)
    pages_processed = Column(Integer, nullable=False, default=0)
    extracted_text = Column(Text, nullable=False, default="")
    table_count = Column(Integer, nullable=False, default=0)
    ocr_completed_published = Column(Boolean, nullable=False, default=False)
    parsing_requested_published = Column(Boolean, nullable=False, default=False)
    log_entries_json = Column(Text, nullable=False, default="[]")
    error_message = Column(Text, nullable=True)
    received_at = Column(String(40), nullable=False)
    completed_at = Column(String(40), nullable=True)


class OcrExtractedTableModel(Base):
    """UC-030 bước 3-4: 1 bảng trích xuất được từ tài liệu PDF/scan."""

    __tablename__ = "ocr_extracted_tables"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    ocr_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}ocr_jobs.id"), nullable=False, index=True
    )
    table_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    rows_json = Column(Text, nullable=False)