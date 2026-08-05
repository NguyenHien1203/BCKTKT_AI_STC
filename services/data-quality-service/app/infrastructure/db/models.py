"""SQLAlchemy models cho data-quality-service — UC-029."""
import os

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

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


class MappingRuleModel(Base):
    __tablename__ = "mapping_rules"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=True, index=True)
    field_name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    rule_type = Column(String(20), nullable=False)
    catalog_map_json = Column(Text, nullable=False, default="{}")
    normalize_case = Column(String(10), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(String(40), nullable=False)


class MappingJobModel(Base):
    __tablename__ = "mapping_jobs"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    parsing_job_id = Column(Integer, nullable=False, index=True)
    dataset_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="RECEIVED", index=True)
    records_total = Column(Integer, nullable=False, default=0)
    records_mapped = Column(Integer, nullable=False, default=0)
    records_rejected = Column(Integer, nullable=False, default=0)
    unmapped_values_count = Column(Integer, nullable=False, default=0)
    log_entries_json = Column(Text, nullable=False, default="[]")
    error_message = Column(Text, nullable=True)
    received_at = Column(String(40), nullable=False)
    completed_at = Column(String(40), nullable=True)


class MappingRejectionModel(Base):
    __tablename__ = "mapping_rejections"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}mapping_jobs.id"), nullable=False, index=True
    )
    row_index = Column(Integer, nullable=False)
    field_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    rejected_at = Column(String(40), nullable=False)


class UnmappedQueueItemModel(Base):
    __tablename__ = "unmapped_value_queue"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}mapping_jobs.id"), nullable=False, index=True
    )
    dataset_id = Column(Integer, nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    field_name = Column(String(255), nullable=False)
    raw_value = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    # ---- UC-032 Xử lý hàng đợi chưa ánh xạ (bước 2: MAP/CREATE_NEW/REJECT) ----
    resolution_action = Column(String(20), nullable=True)
    resolved_value = Column(Text, nullable=True)
    resolution_reason = Column(Text, nullable=True)
    resolved_at = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)


class MappedStandardRecordModel(Base):
    __tablename__ = "mapped_standard_records"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_job_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}mapping_jobs.id"), nullable=False, index=True
    )
    row_index = Column(Integer, nullable=False)
    standardized_fields_json = Column(Text, nullable=False)


class OrgUnitCatalogModel(Base):
    """UC-033: 1 đơn vị trong danh mục đơn vị (cây phân cấp)."""

    __tablename__ = "org_unit_catalog"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    unit_type = Column(String(20), nullable=False)
    parent_id = Column(Integer, nullable=True, index=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    version = Column(Integer, nullable=False, default=1)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    lifecycle_action = Column(String(20), nullable=True)
    lifecycle_note = Column(Text, nullable=True)
    split_from_id = Column(Integer, nullable=True)
    merged_from_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class OrgUnitCatalogVersionModel(Base):
    """UC-033 bước 2-3: lịch sử phiên bản (append-only) của 1 đơn vị."""

    __tablename__ = "org_unit_catalog_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}org_unit_catalog.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    unit_type = Column(String(20), nullable=False)
    parent_id = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)


class BudgetItemCatalogModel(Base):
    """UC-034: 1 khoản mục trong danh mục khoản mục NSNN (cây

    Chương/Loại/Khoản/Mục/Tiểu mục), theo năm ngân sách."""

    __tablename__ = "budget_item_catalog"
    __table_args__ = (
        UniqueConstraint("code", "budget_year", name="uq_budget_item_catalog_code_year"),
        *([_table_args] if _SCHEMA else []),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    level = Column(String(20), nullable=False)
    budget_year = Column(Integer, nullable=False, index=True)
    parent_id = Column(Integer, nullable=True, index=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    version = Column(Integer, nullable=False, default=1)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class BudgetItemCatalogVersionModel(Base):
    """UC-034 bước 2: lịch sử phiên bản (append-only) của 1 khoản mục NSNN."""

    __tablename__ = "budget_item_catalog_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}budget_item_catalog.id"), nullable=False, index=True
    )
    budget_year = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    level = Column(String(20), nullable=False)
    parent_id = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)


class BudgetItemChangeRequestModel(Base):
    """UC-034 bước 3: đề nghị thay đổi khoản mục nhạy cảm -- hàng đợi

    chờ duyệt."""

    __tablename__ = "budget_item_change_requests"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}budget_item_catalog.id"), nullable=False, index=True
    )
    budget_year = Column(Integer, nullable=False)
    requested_by = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    proposed_name = Column(String(255), nullable=True)
    proposed_status = Column(String(20), nullable=True)
    proposed_is_sensitive = Column(Boolean, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    reviewed_by = Column(String(255), nullable=True)
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)

class AssetGroupCatalogModel(Base):
    """UC-035: 1 nhóm tài sản trong danh mục nhóm tài sản cố định (TT45,

    sửa đổi TT162 -- gọi tắt TT48/TT162 theo docs/use_cases.json)."""

    __tablename__ = "asset_group_catalog"
    __table_args__ = (
        UniqueConstraint("code", name="uq_asset_group_catalog_code"),
        *([_table_args] if _SCHEMA else []),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    regulation = Column(String(20), nullable=False, index=True)
    useful_life_years = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    version = Column(Integer, nullable=False, default=1)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class AssetGroupCatalogVersionModel(Base):
    """UC-035 bước 2: lịch sử phiên bản (append-only) của 1 nhóm tài sản."""

    __tablename__ = "asset_group_catalog_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}asset_group_catalog.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    regulation = Column(String(20), nullable=False)
    useful_life_years = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)


class AssetDepreciationRateModel(Base):
    """UC-035 bước 3: khai báo tỉ lệ khấu hao theo nhóm tài sản

    (append-only -- mỗi lượt khai báo là 1 bản ghi)."""

    __tablename__ = "asset_depreciation_rates"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_group_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}asset_group_catalog.id"), nullable=False, index=True
    )
    depreciation_rate_percent = Column(Float, nullable=False)
    useful_life_years = Column(Integer, nullable=True)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    note = Column(Text, nullable=True)
    declared_by = Column(String(255), nullable=True)
    created_at = Column(String(40), nullable=False)

# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


class CatalogEntryModel(Base):
    """UC-036: 1 mục trong 1 trong 3 danh mục dùng chung (mặt hàng /

    loại văn bản / nguồn vốn), phân biệt bởi `catalog_type`."""

    __tablename__ = "catalog_entries"
    __table_args__ = (
        UniqueConstraint(
            "code", "catalog_type", name="uq_catalog_entries_code_catalog_type"
        ),
        *([_table_args] if _SCHEMA else []),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_type = Column(String(30), nullable=False, index=True)
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    version = Column(Integer, nullable=False, default=1)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    effective_from = Column(String(40), nullable=True)
    effective_to = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class CatalogEntryVersionModel(Base):
    """UC-036 bước 2: lịch sử phiên bản (append-only) của 1 mục danh mục."""

    __tablename__ = "catalog_entry_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}catalog_entries.id"), nullable=False, index=True
    )
    catalog_type = Column(String(30), nullable=False)
    version = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)


class CatalogChangeRequestModel(Base):
    """UC-036 bước 3: đề nghị thay đổi danh mục nhạy cảm -- hàng đợi chờ

    duyệt (xem UC-037)."""

    __tablename__ = "catalog_change_requests"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}catalog_entries.id"), nullable=False, index=True
    )
    catalog_type = Column(String(30), nullable=False, index=True)
    requested_by = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    proposed_name = Column(String(255), nullable=True)
    proposed_unit = Column(String(50), nullable=True)
    proposed_description = Column(Text, nullable=True)
    proposed_status = Column(String(20), nullable=True)
    proposed_is_sensitive = Column(Boolean, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    reviewed_by = Column(String(255), nullable=True)
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)

# ---------- UC-037: Phê duyệt thay đổi danh mục nhạy cảm ----------


class CatalogChangeAuditLogModel(Base):
    """UC-037 bước 4: nhật ký append-only các quyết định phê

    duyệt/từ chối yêu cầu thay đổi danh mục nhạy cảm (UC-036 bước 3)."""

    __tablename__ = "catalog_change_audit_logs"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}catalog_change_requests.id"), nullable=False, index=True
    )
    entry_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}catalog_entries.id"), nullable=False, index=True
    )
    catalog_type = Column(String(30), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)
    decided_by = Column(String(255), nullable=False)
    decision_reason = Column(Text, nullable=False)
    diff_snapshot = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)

# ---------- UC-038: Quản lý quy tắc kiểm tra chất lượng ----------


class QualityRuleModel(Base):
    """UC-038: 1 quy tắc kiểm tra chất lượng dữ liệu (`metadata.quality_rules`)."""

    __tablename__ = "quality_rules"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=True, index=True)
    field_names_json = Column(Text, nullable=False, default="[]")
    rule_type = Column(String(20), nullable=False, index=True)
    params_json = Column(Text, nullable=False, default="{}")
    weight = Column(Float, nullable=False, default=1.0)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class QualityRuleVersionModel(Base):
    """UC-038 bước 2: lịch sử phiên bản (append-only) của 1 quy tắc chất lượng."""

    __tablename__ = "quality_rule_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(
        Integer, ForeignKey(f"{_fk_prefix}quality_rules.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    dataset_id = Column(Integer, nullable=True)
    field_names_json = Column(Text, nullable=False, default="[]")
    rule_type = Column(String(20), nullable=False)
    params_json = Column(Text, nullable=False, default="{}")
    weight = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, nullable=False, default=True)
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)


class QualityScoreConfigModel(Base):
    """UC-038 bước 3: cấu hình ngưỡng + trọng số cho điểm chất lượng theo tập dữ liệu."""

    __tablename__ = "quality_score_configs"
    __table_args__ = (
        UniqueConstraint("dataset_id", name="uq_quality_score_configs_dataset_id"),
        *([_table_args] if _SCHEMA else []),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=True, unique=True, index=True)
    pass_threshold = Column(Float, nullable=False)
    rule_type_weights_json = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)


class QualityScoreConfigVersionModel(Base):
    """UC-038 bước 3: lịch sử phiên bản (append-only) của 1 cấu hình điểm chất lượng."""

    __tablename__ = "quality_score_config_versions"
    __table_args__ = _table_args

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer,
        ForeignKey(f"{_fk_prefix}quality_score_configs.id"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    dataset_id = Column(Integer, nullable=True)
    pass_threshold = Column(Float, nullable=False)
    rule_type_weights_json = Column(Text, nullable=False, default="{}")
    change_note = Column(Text, nullable=True)
    changed_at = Column(String(40), nullable=False)