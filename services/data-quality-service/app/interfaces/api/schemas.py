from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str


class SchemaFieldInput(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    description: str = ""


class ParsingRequestedEvent(BaseModel):
    """Body của endpoint nhận sự kiện `parsing.requested` (bước 1).

    Trong hệ thống thật, sự kiện này được RabbitMQ đẩy tới và 1 consumer/
    worker của data-quality-service gọi thẳng use case
    `StructuredParsingService.receive_and_process()` — endpoint này mô
    phỏng đúng payload sự kiện đó (xem
    `ingestion-service/app/application/use_cases/sync_incremental.py`,
    hàm `_events.publish("parsing.requested", ...)`) để có thể kích hoạt
    thủ công lúc test/vận hành, cùng tinh thần với UC-025 (nút "chạy thủ
    công" gọi thẳng cùng 1 use case mà hệ thống tự động cũng dùng).
    """

    dataset_id: int
    raw_object_key: str
    schema_fields: List[SchemaFieldInput]
    source_format: Optional[str] = Field(
        default=None,
        description="CSV/EXCEL/JSON/XML — nếu không truyền, hệ thống tự suy luận theo đuôi tệp",
    )
    field_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Ánh xạ tường minh tên cột nguồn -> tên trường đích; nếu để trống, hệ thống tự ánh xạ theo tên trùng khớp",
    )
    ingestion_run_id: Optional[int] = None
    data_source_id: Optional[int] = None


class ParsingJobResponse(BaseModel):
    id: int
    dataset_id: int
    ingestion_run_id: Optional[int]
    data_source_id: Optional[int]
    source_format: str
    raw_object_key: str
    schema_fields: List[Dict[str, Any]]
    field_mapping: Dict[str, str]
    status: str
    records_read: int
    records_parsed: int
    records_failed: int
    mapping_event_published: bool
    log_entries: List[Dict[str, str]]
    error_message: Optional[str]
    received_at: str
    completed_at: Optional[str]

    @classmethod
    def from_entity(cls, job) -> "ParsingJobResponse":
        return cls(
            id=job.id,
            dataset_id=job.dataset_id,
            ingestion_run_id=job.ingestion_run_id,
            data_source_id=job.data_source_id,
            source_format=job.source_format,
            raw_object_key=job.raw_object_key,
            schema_fields=job.schema_fields,
            field_mapping=job.field_mapping,
            status=job.status,
            records_read=job.records_read,
            records_parsed=job.records_parsed,
            records_failed=job.records_failed,
            mapping_event_published=job.mapping_event_published,
            log_entries=job.log_entries,
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )


class ParsingRowErrorResponse(BaseModel):
    id: int
    parsing_job_id: int
    row_index: int
    field_name: str
    message: str

    @classmethod
    def from_entity(cls, err) -> "ParsingRowErrorResponse":
        return cls(
            id=err.id,
            parsing_job_id=err.parsing_job_id,
            row_index=err.row_index,
            field_name=err.field_name,
            message=err.message,
        )


class ParsedRecordResponse(BaseModel):
    row_index: int
    mapped_fields: Dict[str, Any]
    has_error: bool

    @classmethod
    def from_entity(cls, rec) -> "ParsedRecordResponse":
        return cls(row_index=rec.row_index, mapped_fields=rec.mapped_fields, has_error=rec.has_error)


# ---------- UC-030: Phân tích PDF/bản quét + OCR ----------


class OcrRequestedEvent(BaseModel):
    """Body của endpoint nhận sự kiện `ocr.requested` (bước 1).

    Mô phỏng đúng payload sự kiện thật do ingestion-service (UC-024) phát
    ra — xem
    `ingestion-service/app/application/use_cases/manage_van_ban_intake.py`,
    hàm `_events.publish("ocr.requested", {...})` — để có thể kích hoạt
    thủ công lúc test/vận hành, cùng tinh thần với `ParsingRequestedEvent`
    (UC-029).
    """

    raw_object_key: str
    van_ban_intake_id: Optional[int] = None
    data_source_id: Optional[int] = None
    so_ky_hieu: Optional[str] = None
    engine: Optional[str] = Field(
        default=None,
        description="PADDLEOCR/OLMOCR — mặc định PADDLEOCR nếu không truyền",
    )


class OcrJobResponse(BaseModel):
    id: int
    van_ban_intake_id: Optional[int]
    data_source_id: Optional[int]
    so_ky_hieu: Optional[str]
    raw_object_key: str
    engine_requested: str
    engine_used: Optional[str]
    status: str
    pages_processed: int
    extracted_text: str
    table_count: int
    ocr_completed_published: bool
    parsing_requested_published: bool
    log_entries: List[Dict[str, str]]
    error_message: Optional[str]
    received_at: str
    completed_at: Optional[str]

    @classmethod
    def from_entity(cls, job) -> "OcrJobResponse":
        return cls(
            id=job.id,
            van_ban_intake_id=job.van_ban_intake_id,
            data_source_id=job.data_source_id,
            so_ky_hieu=job.so_ky_hieu,
            raw_object_key=job.raw_object_key,
            engine_requested=job.engine_requested,
            engine_used=job.engine_used,
            status=job.status,
            pages_processed=job.pages_processed,
            extracted_text=job.extracted_text,
            table_count=job.table_count,
            ocr_completed_published=job.ocr_completed_published,
            parsing_requested_published=job.parsing_requested_published,
            log_entries=job.log_entries,
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )


class OcrExtractedTableResponse(BaseModel):
    id: int
    ocr_job_id: int
    table_index: int
    page_number: int
    rows: List[List[Any]]

    @classmethod
    def from_entity(cls, t) -> "OcrExtractedTableResponse":
        return cls(
            id=t.id,
            ocr_job_id=t.ocr_job_id,
            table_index=t.table_index,
            page_number=t.page_number,
            rows=t.rows,
        )

# ---------- UC-031: Ánh xạ trường sang dạng chuẩn ----------


class MappingRuleCreate(BaseModel):
    """Đăng ký 1 quy tắc ánh xạ (input bắt buộc cho bước 1 của UC-031 --

    xem ghi chú ở `app/application/use_cases/manage_mapping_rule.py`).
    """

    field_name: str
    version: int = 1
    rule_type: str = Field(description="DIRECT hoặc CATALOG_LOOKUP")
    dataset_id: Optional[int] = Field(
        default=None, description="Để trống = quy tắc chung áp dụng mọi tập dữ liệu"
    )
    catalog_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Bắt buộc khi rule_type=CATALOG_LOOKUP: giá trị nguồn (đã chuẩn hoá trim+upper) -> giá trị chuẩn",
    )
    normalize_case: Optional[str] = Field(default=None, description="UPPER/LOWER, dùng cho rule_type=DIRECT")
    is_active: bool = True


class MappingRuleResponse(BaseModel):
    id: int
    dataset_id: Optional[int]
    field_name: str
    version: int
    rule_type: str
    catalog_map: Dict[str, str]
    normalize_case: Optional[str]
    is_active: bool
    created_at: str

    @classmethod
    def from_entity(cls, rule) -> "MappingRuleResponse":
        return cls(
            id=rule.id,
            dataset_id=rule.dataset_id,
            field_name=rule.field_name,
            version=rule.version,
            rule_type=rule.rule_type,
            catalog_map=rule.catalog_map,
            normalize_case=rule.normalize_case,
            is_active=rule.is_active,
            created_at=rule.created_at,
        )


class MappingRequestedEvent(BaseModel):
    """Body của endpoint nhận sự kiện `mapping.requested` (phát bởi

    UC-029/UC-030 sau khi ánh xạ tên trường + ép kiểu xong -- xem
    `app/application/use_cases/parse_structured_data.py`,
    `MAPPING_REQUESTED_EVENT`). Mô phỏng đúng payload sự kiện thật, cùng
    tinh thần `ParsingRequestedEvent` (UC-029).
    """

    parsing_job_id: int
    dataset_id: Optional[int] = Field(
        default=None, description="Để trống thì lấy theo dataset_id của parsing_job_id"
    )


class MappingJobResponse(BaseModel):
    id: int
    parsing_job_id: int
    dataset_id: int
    status: str
    records_total: int
    records_mapped: int
    records_rejected: int
    unmapped_values_count: int
    log_entries: List[Dict[str, str]]
    error_message: Optional[str]
    received_at: str
    completed_at: Optional[str]

    @classmethod
    def from_entity(cls, job) -> "MappingJobResponse":
        return cls(
            id=job.id,
            parsing_job_id=job.parsing_job_id,
            dataset_id=job.dataset_id,
            status=job.status,
            records_total=job.records_total,
            records_mapped=job.records_mapped,
            records_rejected=job.records_rejected,
            unmapped_values_count=job.unmapped_values_count,
            log_entries=job.log_entries,
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )


class MappingRejectionResponse(BaseModel):
    id: int
    mapping_job_id: int
    row_index: int
    field_name: str
    reason: str
    rejected_at: str

    @classmethod
    def from_entity(cls, r) -> "MappingRejectionResponse":
        return cls(
            id=r.id,
            mapping_job_id=r.mapping_job_id,
            row_index=r.row_index,
            field_name=r.field_name,
            reason=r.reason,
            rejected_at=r.rejected_at,
        )


class UnmappedQueueItemResponse(BaseModel):
    id: int
    mapping_job_id: int
    dataset_id: int
    row_index: int
    field_name: str
    raw_value: str
    status: str
    resolution_action: Optional[str] = None
    resolved_value: Optional[str] = None
    resolution_reason: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, it) -> "UnmappedQueueItemResponse":
        return cls(
            id=it.id,
            mapping_job_id=it.mapping_job_id,
            dataset_id=it.dataset_id,
            row_index=it.row_index,
            field_name=it.field_name,
            raw_value=it.raw_value,
            status=it.status,
            resolution_action=it.resolution_action,
            resolved_value=it.resolved_value,
            resolution_reason=it.resolution_reason,
            resolved_at=it.resolved_at,
            created_at=it.created_at,
        )


# ---------- UC-032: Xử lý hàng đợi chưa ánh xạ ----------


class ResolveUnmappedQueueRequest(BaseModel):
    """Body của endpoint xử lý 1 mục hàng đợi chưa ánh xạ (bước 2 UC-032)."""

    action: str = Field(description="MAP (ánh xạ) / CREATE_NEW (tạo mục mới) / REJECT (từ chối)")
    standard_value: Optional[str] = Field(
        default=None, description="Giá trị chuẩn -- bắt buộc khi action=MAP hoặc CREATE_NEW"
    )
    reason: Optional[str] = Field(
        default=None, description="Lý do từ chối -- bắt buộc khi action=REJECT"
    )
    apply_to_similar: bool = Field(
        default=False,
        description=(
            "Bước 3 'Ánh xạ hàng loạt các giá trị tương tự': True để áp dụng đồng loạt "
            "kết quả xử lý này cho các mục PENDING khác cùng dataset_id/field_name/raw_value"
        ),
    )


class ResolveUnmappedQueueResponse(BaseModel):
    item: UnmappedQueueItemResponse
    updated_rule: Optional[MappingRuleResponse] = None
    affected_items: List[UnmappedQueueItemResponse] = Field(default_factory=list)
    affected_count: int = 0

    @classmethod
    def from_result(cls, result) -> "ResolveUnmappedQueueResponse":
        affected = [UnmappedQueueItemResponse.from_entity(i) for i in result.affected_items]
        return cls(
            item=UnmappedQueueItemResponse.from_entity(result.item),
            updated_rule=(
                MappingRuleResponse.from_entity(result.updated_rule)
                if result.updated_rule is not None
                else None
            ),
            affected_items=affected,
            affected_count=len(affected),
        )


class MappedStandardRecordResponse(BaseModel):
    row_index: int
    standardized_fields: Dict[str, Any]

    @classmethod
    def from_entity(cls, rec) -> "MappedStandardRecordResponse":
        return cls(row_index=rec.row_index, standardized_fields=rec.standardized_fields)

# ---------- UC-033: Quản lý danh mục đơn vị ----------


class OrgUnitCatalogResponse(BaseModel):
    id: int
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int] = None
    status: str
    version: int
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    lifecycle_action: Optional[str] = None
    lifecycle_note: Optional[str] = None
    split_from_id: Optional[int] = None
    merged_from_ids: List[int] = Field(default_factory=list)
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, u) -> "OrgUnitCatalogResponse":
        return cls(
            id=u.id,
            code=u.code,
            name=u.name,
            unit_type=u.unit_type,
            parent_id=u.parent_id,
            status=u.status,
            version=u.version,
            effective_from=u.effective_from,
            effective_to=u.effective_to,
            lifecycle_action=u.lifecycle_action,
            lifecycle_note=u.lifecycle_note,
            split_from_id=u.split_from_id,
            merged_from_ids=u.merged_from_ids,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )


class OrgUnitTreeNodeResponse(BaseModel):
    unit: OrgUnitCatalogResponse
    children: List["OrgUnitTreeNodeResponse"] = Field(default_factory=list)

    @classmethod
    def from_node(cls, node) -> "OrgUnitTreeNodeResponse":
        return cls(
            unit=OrgUnitCatalogResponse.from_entity(node.unit),
            children=[cls.from_node(c) for c in node.children],
        )


OrgUnitTreeNodeResponse.model_rebuild()


class OrgUnitCatalogVersionResponse(BaseModel):
    id: int
    unit_id: int
    version: int
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int] = None
    status: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "OrgUnitCatalogVersionResponse":
        return cls(
            id=v.id,
            unit_id=v.unit_id,
            version=v.version,
            code=v.code,
            name=v.name,
            unit_type=v.unit_type,
            parent_id=v.parent_id,
            status=v.status,
            effective_from=v.effective_from,
            effective_to=v.effective_to,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class OrgUnitCatalogCreate(BaseModel):
    """Bước 2 'Thêm đơn vị mới'."""

    code: str
    name: str
    unit_type: str = Field(description="SO / PHONG / XA")
    parent_id: Optional[int] = None
    effective_from: Optional[str] = None
    note: Optional[str] = None


class OrgUnitCatalogUpdate(BaseModel):
    """Bước 3 'Sửa thông tin đơn vị'. Trường không truyền (None) giữ

    nguyên giá trị cũ; để đổi `parent_id` về gốc (None), truyền
    `clear_parent=true`."""

    name: Optional[str] = None
    unit_type: Optional[str] = None
    parent_id: Optional[int] = None
    clear_parent: bool = False
    note: Optional[str] = None


class CloseOrgUnitRequest(BaseModel):
    effective_to: str
    note: Optional[str] = None


class SplitOrgUnitChildInput(BaseModel):
    code: str
    name: str
    unit_type: Optional[str] = None


class SplitOrgUnitRequest(BaseModel):
    effective_from: str
    new_units: List[SplitOrgUnitChildInput]
    note: Optional[str] = None


class SplitOrgUnitResponse(BaseModel):
    source: OrgUnitCatalogResponse
    created_units: List[OrgUnitCatalogResponse]

    @classmethod
    def from_result(cls, result) -> "SplitOrgUnitResponse":
        return cls(
            source=OrgUnitCatalogResponse.from_entity(result.source),
            created_units=[OrgUnitCatalogResponse.from_entity(u) for u in result.created_units],
        )


class MergeOrgUnitTargetInput(BaseModel):
    code: str
    name: str
    unit_type: Optional[str] = None
    parent_id: Optional[int] = None


class MergeOrgUnitRequest(BaseModel):
    source_unit_ids: List[int]
    target: MergeOrgUnitTargetInput
    effective_from: str
    note: Optional[str] = None


class MergeOrgUnitResponse(BaseModel):
    source_units: List[OrgUnitCatalogResponse]
    merged_unit: OrgUnitCatalogResponse

    @classmethod
    def from_result(cls, result) -> "MergeOrgUnitResponse":
        return cls(
            source_units=[OrgUnitCatalogResponse.from_entity(u) for u in result.source_units],
            merged_unit=OrgUnitCatalogResponse.from_entity(result.merged_unit),
        )

class BudgetItemCatalogResponse(BaseModel):
    id: int
    code: str
    name: str
    level: str
    budget_year: int
    parent_id: Optional[int] = None
    status: str
    version: int
    is_sensitive: bool
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, i) -> "BudgetItemCatalogResponse":
        return cls(
            id=i.id,
            code=i.code,
            name=i.name,
            level=i.level,
            budget_year=i.budget_year,
            parent_id=i.parent_id,
            status=i.status,
            version=i.version,
            is_sensitive=i.is_sensitive,
            effective_from=i.effective_from,
            effective_to=i.effective_to,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )


class BudgetItemTreeNodeResponse(BaseModel):
    item: BudgetItemCatalogResponse
    children: List["BudgetItemTreeNodeResponse"] = Field(default_factory=list)

    @classmethod
    def from_node(cls, node) -> "BudgetItemTreeNodeResponse":
        return cls(
            item=BudgetItemCatalogResponse.from_entity(node.item),
            children=[cls.from_node(c) for c in node.children],
        )


BudgetItemTreeNodeResponse.model_rebuild()


class BudgetItemCatalogVersionResponse(BaseModel):
    id: int
    item_id: int
    budget_year: int
    version: int
    code: str
    name: str
    level: str
    parent_id: Optional[int] = None
    status: str
    is_sensitive: bool
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "BudgetItemCatalogVersionResponse":
        return cls(
            id=v.id,
            item_id=v.item_id,
            budget_year=v.budget_year,
            version=v.version,
            code=v.code,
            name=v.name,
            level=v.level,
            parent_id=v.parent_id,
            status=v.status,
            is_sensitive=v.is_sensitive,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class BudgetItemCatalogCreate(BaseModel):
    """Bước 2 'Thêm entry'."""

    code: str
    name: str
    level: str = Field(description="CHUONG / LOAI / KHOAN / MUC / TIEU_MUC")
    budget_year: int
    parent_id: Optional[int] = None
    is_sensitive: bool = False
    effective_from: Optional[str] = None
    note: Optional[str] = None


class BudgetItemCatalogUpdate(BaseModel):
    """Bước 2 'Sửa entry' -- KHÔNG áp dụng cho khoản mục nhạy cảm (dùng

    bước 3 'Đề nghị thay đổi' thay thế)."""

    name: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class BudgetItemChangeRequestResponse(BaseModel):
    id: int
    item_id: int
    budget_year: int
    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None
    status: str
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, r) -> "BudgetItemChangeRequestResponse":
        return cls(
            id=r.id,
            item_id=r.item_id,
            budget_year=r.budget_year,
            requested_by=r.requested_by,
            reason=r.reason,
            proposed_name=r.proposed_name,
            proposed_status=r.proposed_status,
            proposed_is_sensitive=r.proposed_is_sensitive,
            status=r.status,
            reviewed_by=r.reviewed_by,
            review_note=r.review_note,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        )


class BudgetItemChangeRequestCreate(BaseModel):
    """Bước 3 'Đề nghị thay đổi khoản mục nhạy cảm'."""

    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None


class BudgetItemChangeReviewRequest(BaseModel):
    """Duyệt / từ chối 1 yêu cầu thay đổi (bước 3)."""

    reviewed_by: str
    review_note: Optional[str] = None

# ---------- UC-035: Quản lý danh mục nhóm tài sản ----------


class AssetGroupCatalogResponse(BaseModel):
    id: int
    code: str
    name: str
    regulation: str
    useful_life_years: Optional[int] = None
    status: str
    version: int
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    note: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, g) -> "AssetGroupCatalogResponse":
        return cls(
            id=g.id,
            code=g.code,
            name=g.name,
            regulation=g.regulation,
            useful_life_years=g.useful_life_years,
            status=g.status,
            version=g.version,
            effective_from=g.effective_from,
            effective_to=g.effective_to,
            note=g.note,
            created_at=g.created_at,
            updated_at=g.updated_at,
        )


class AssetGroupCatalogVersionResponse(BaseModel):
    id: int
    group_id: int
    version: int
    code: str
    name: str
    regulation: str
    useful_life_years: Optional[int] = None
    status: str
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "AssetGroupCatalogVersionResponse":
        return cls(
            id=v.id,
            group_id=v.group_id,
            version=v.version,
            code=v.code,
            name=v.name,
            regulation=v.regulation,
            useful_life_years=v.useful_life_years,
            status=v.status,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class AssetGroupCatalogCreate(BaseModel):
    """Bước 2 'Thêm entry'."""

    code: str
    name: str
    regulation: str = Field(description="TT45 (Thông tư 45/2018/TT-BTC) hoặc TT162")
    useful_life_years: Optional[int] = None
    effective_from: Optional[str] = None
    note: Optional[str] = None


class AssetGroupCatalogUpdate(BaseModel):
    """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản."""

    name: Optional[str] = None
    regulation: Optional[str] = None
    useful_life_years: Optional[int] = None
    clear_useful_life_years: bool = Field(
        default=False,
        description="True để xoá useful_life_years hiện có (thay vì giữ nguyên)",
    )
    status: Optional[str] = None
    note: Optional[str] = None


class AssetDepreciationRateResponse(BaseModel):
    id: int
    asset_group_id: int
    depreciation_rate_percent: float
    useful_life_years: Optional[int] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    note: Optional[str] = None
    declared_by: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, r) -> "AssetDepreciationRateResponse":
        return cls(
            id=r.id,
            asset_group_id=r.asset_group_id,
            depreciation_rate_percent=r.depreciation_rate_percent,
            useful_life_years=r.useful_life_years,
            effective_from=r.effective_from,
            effective_to=r.effective_to,
            note=r.note,
            declared_by=r.declared_by,
            created_at=r.created_at,
        )


class AssetDepreciationRateDeclare(BaseModel):
    """Bước 3 'Khai báo tỉ lệ khấu hao theo nhóm' -- hệ thống lưu."""

    depreciation_rate_percent: float = Field(gt=0, le=100)
    useful_life_years: Optional[int] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    note: Optional[str] = None
    declared_by: Optional[str] = None

# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


class CatalogEntryResponse(BaseModel):
    id: int
    catalog_type: str
    code: str
    name: str
    unit: Optional[str] = None
    description: Optional[str] = None
    status: str
    version: int
    is_sensitive: bool
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, e) -> "CatalogEntryResponse":
        return cls(
            id=e.id,
            catalog_type=e.catalog_type,
            code=e.code,
            name=e.name,
            unit=e.unit,
            description=e.description,
            status=e.status,
            version=e.version,
            is_sensitive=e.is_sensitive,
            effective_from=e.effective_from,
            effective_to=e.effective_to,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class CatalogEntryVersionResponse(BaseModel):
    id: int
    entry_id: int
    catalog_type: str
    version: int
    code: str
    name: str
    unit: Optional[str] = None
    status: str
    is_sensitive: bool
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "CatalogEntryVersionResponse":
        return cls(
            id=v.id,
            entry_id=v.entry_id,
            catalog_type=v.catalog_type,
            version=v.version,
            code=v.code,
            name=v.name,
            unit=v.unit,
            status=v.status,
            is_sensitive=v.is_sensitive,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class CatalogEntryCreate(BaseModel):
    """Bước 2 'Thêm entry'."""

    catalog_type: str = Field(description="ITEM / DOCUMENT_TYPE / FUNDING_SOURCE")
    code: str
    name: str
    unit: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: bool = False
    effective_from: Optional[str] = None
    note: Optional[str] = None


class CatalogEntryUpdate(BaseModel):
    """Bước 2 'Sửa entry' -- KHÔNG áp dụng cho mục nhạy cảm (dùng bước 3

    'Đề nghị thay đổi' thay thế)."""

    name: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class CatalogChangeRequestResponse(BaseModel):
    id: int
    entry_id: int
    catalog_type: str
    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_unit: Optional[str] = None
    proposed_description: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None
    status: str
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, r) -> "CatalogChangeRequestResponse":
        return cls(
            id=r.id,
            entry_id=r.entry_id,
            catalog_type=r.catalog_type,
            requested_by=r.requested_by,
            reason=r.reason,
            proposed_name=r.proposed_name,
            proposed_unit=r.proposed_unit,
            proposed_description=r.proposed_description,
            proposed_status=r.proposed_status,
            proposed_is_sensitive=r.proposed_is_sensitive,
            status=r.status,
            reviewed_by=r.reviewed_by,
            review_note=r.review_note,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        )


class CatalogChangeRequestCreate(BaseModel):
    """Bước 3 'Đề nghị thay đổi danh mục nhạy cảm'."""

    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_unit: Optional[str] = None
    proposed_description: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None


class CatalogChangeReviewRequest(BaseModel):
    """Duyệt / từ chối 1 yêu cầu thay đổi (bước 3, dùng bởi UC-037)."""

    reviewed_by: str
    review_note: Optional[str] = None

# ---------- UC-037: Phê duyệt thay đổi danh mục nhạy cảm ----------


class CatalogChangeDiffFieldResponse(BaseModel):
    """Bước 2 'Hệ thống hiển thị diff' -- 1 trường được đề nghị thay đổi."""

    field: str
    field_label: str
    old_value: Any = None
    new_value: Any = None
    changed: bool

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CatalogChangeDiffFieldResponse":
        return cls(**d)


class CatalogChangeDiffResponse(BaseModel):
    """Bước 2 'Hệ thống hiển thị diff' cho 1 yêu cầu thay đổi cụ thể."""

    request: CatalogChangeRequestResponse
    entry: CatalogEntryResponse
    changes: List[CatalogChangeDiffFieldResponse]


class CatalogChangeApprovalDecision(BaseModel):
    """Bước 3+4+5 'Phê duyệt / từ chối -- ghi lý do phê duyệt' -- khác

    `CatalogChangeReviewRequest` (UC-036) ở chỗ `reason` BẮT BUỘC (UC-037
    bước 5 yêu cầu phải ghi lý do trước khi lưu vào nhật ký)."""

    decided_by: str = Field(description="Người phê duyệt (Lãnh đạo Phòng nghiệp vụ)")
    reason: str = Field(min_length=1, description="Lý do phê duyệt/từ chối -- bắt buộc")


class CatalogChangeAuditLogResponse(BaseModel):
    """Bước 5 'Hệ thống lưu vào nhật ký' -- 1 bản ghi nhật ký phê duyệt."""

    id: int
    request_id: int
    entry_id: int
    catalog_type: str
    action: str
    decided_by: str
    decision_reason: str
    diff_snapshot: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, log) -> "CatalogChangeAuditLogResponse":
        return cls(
            id=log.id,
            request_id=log.request_id,
            entry_id=log.entry_id,
            catalog_type=log.catalog_type,
            action=log.action,
            decided_by=log.decided_by,
            decision_reason=log.decision_reason,
            diff_snapshot=log.diff_snapshot,
            created_at=log.created_at,
        )


class CatalogChangeApprovalResultResponse(BaseModel):
    """Kết quả bước 3+4 'Phê duyệt' -- mục danh mục sau khi áp dụng +

    bản ghi nhật ký vừa ghi (bước 5)."""

    entry: CatalogEntryResponse
    audit_log: CatalogChangeAuditLogResponse


class CatalogChangeRejectionResultResponse(BaseModel):
    """Kết quả bước 3 'Từ chối' -- yêu cầu sau khi từ chối + bản ghi

    nhật ký vừa ghi (bước 5)."""

    request: CatalogChangeRequestResponse
    audit_log: CatalogChangeAuditLogResponse

# ---------- UC-038: Quản lý quy tắc kiểm tra chất lượng ----------


class QualityRuleResponse(BaseModel):
    id: int
    dataset_id: Optional[int] = None
    field_names: List[str]
    rule_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    weight: float
    description: Optional[str] = None
    is_active: bool
    version: int
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, r) -> "QualityRuleResponse":
        return cls(
            id=r.id,
            dataset_id=r.dataset_id,
            field_names=r.field_names,
            rule_type=r.rule_type,
            params=r.params,
            weight=r.weight,
            description=r.description,
            is_active=r.is_active,
            version=r.version,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


class QualityRuleVersionResponse(BaseModel):
    id: int
    rule_id: int
    version: int
    dataset_id: Optional[int] = None
    field_names: List[str]
    rule_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    weight: float
    is_active: bool
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "QualityRuleVersionResponse":
        return cls(
            id=v.id,
            rule_id=v.rule_id,
            version=v.version,
            dataset_id=v.dataset_id,
            field_names=v.field_names,
            rule_type=v.rule_type,
            params=v.params,
            weight=v.weight,
            is_active=v.is_active,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class QualityRuleCreate(BaseModel):
    """Bước 2 'Thêm quy tắc'."""

    field_names: List[str] = Field(min_length=1)
    rule_type: str = Field(description="COMPLETENESS / VALIDITY / UNIQUENESS / CONSISTENCY")
    dataset_id: Optional[int] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    description: Optional[str] = None
    is_active: bool = True
    note: Optional[str] = None


class QualityRuleUpdate(BaseModel):
    """Bước 2 'Sửa quy tắc'."""

    field_names: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None
    weight: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class QualityScoreConfigResponse(BaseModel):
    id: int
    dataset_id: Optional[int] = None
    pass_threshold: float
    rule_type_weights: Dict[str, float] = Field(default_factory=dict)
    version: int
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, c) -> "QualityScoreConfigResponse":
        return cls(
            id=c.id,
            dataset_id=c.dataset_id,
            pass_threshold=c.pass_threshold,
            rule_type_weights=c.rule_type_weights,
            version=c.version,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class QualityScoreConfigVersionResponse(BaseModel):
    id: int
    config_id: int
    version: int
    dataset_id: Optional[int] = None
    pass_threshold: float
    rule_type_weights: Dict[str, float] = Field(default_factory=dict)
    change_note: Optional[str] = None
    changed_at: str

    @classmethod
    def from_entity(cls, v) -> "QualityScoreConfigVersionResponse":
        return cls(
            id=v.id,
            config_id=v.config_id,
            version=v.version,
            dataset_id=v.dataset_id,
            pass_threshold=v.pass_threshold,
            rule_type_weights=v.rule_type_weights,
            change_note=v.change_note,
            changed_at=v.changed_at,
        )


class QualityScoreConfigSave(BaseModel):
    """Bước 3 'Cấu hình ngưỡng + trọng số cho điểm' -- hệ thống lưu.

    Tạo mới nếu `dataset_id` chưa có cấu hình, ngược lại cập nhật
    (tăng version)."""

    dataset_id: Optional[int] = None
    pass_threshold: float = Field(ge=0, le=100)
    rule_type_weights: Dict[str, float] = Field(default_factory=dict)
    note: Optional[str] = None


# ---------- UC-039: Chạy kiểm tra chất lượng dữ liệu ----------


class MappingCompletedEvent(BaseModel):
    """Payload mô phỏng sự kiện `mapping.completed` (phát bởi UC-031 sau

    khi ánh xạ trường sang dạng chuẩn xong) -- kích hoạt UC-039."""

    mapping_job_id: int
    dataset_id: Optional[int] = None


class QualityCheckJobResponse(BaseModel):
    id: int
    mapping_job_id: int
    dataset_id: Optional[int] = None
    status: str
    pass_threshold: float
    records_checked: int
    overall_score: float
    rule_type_scores: Dict[str, float] = Field(default_factory=dict)
    published_count: int
    exception_count: int
    publish_event_published: bool
    exception_event_published: bool
    log_entries: List[Dict[str, str]] = Field(default_factory=list)
    error_message: Optional[str] = None
    received_at: str
    completed_at: Optional[str] = None

    @classmethod
    def from_entity(cls, j) -> "QualityCheckJobResponse":
        return cls(
            id=j.id,
            mapping_job_id=j.mapping_job_id,
            dataset_id=j.dataset_id,
            status=j.status,
            pass_threshold=j.pass_threshold,
            records_checked=j.records_checked,
            overall_score=j.overall_score,
            rule_type_scores=j.rule_type_scores,
            published_count=j.published_count,
            exception_count=j.exception_count,
            publish_event_published=j.publish_event_published,
            exception_event_published=j.exception_event_published,
            log_entries=j.log_entries,
            error_message=j.error_message,
            received_at=j.received_at,
            completed_at=j.completed_at,
        )


class QualityCheckRuleResultResponse(BaseModel):
    id: int
    quality_check_job_id: int
    rule_id: Optional[int] = None
    rule_type: str
    field_names: List[str]
    total_checked: int
    failed_count: int
    pass_rate: float

    @classmethod
    def from_entity(cls, r) -> "QualityCheckRuleResultResponse":
        return cls(
            id=r.id,
            quality_check_job_id=r.quality_check_job_id,
            rule_id=r.rule_id,
            rule_type=r.rule_type,
            field_names=r.field_names,
            total_checked=r.total_checked,
            failed_count=r.failed_count,
            pass_rate=r.pass_rate,
        )


class QualityPublishedRecordResponse(BaseModel):
    id: int
    quality_check_job_id: int
    dataset_id: Optional[int] = None
    row_index: int
    standardized_fields: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_entity(cls, r) -> "QualityPublishedRecordResponse":
        return cls(
            id=r.id,
            quality_check_job_id=r.quality_check_job_id,
            dataset_id=r.dataset_id,
            row_index=r.row_index,
            standardized_fields=r.standardized_fields,
        )


class QualityExceptionQueueItemResponse(BaseModel):
    id: int
    quality_check_job_id: int
    dataset_id: Optional[int] = None
    row_index: int
    standardized_fields: Dict[str, Any] = Field(default_factory=dict)
    failed_rules: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    created_at: str

    @classmethod
    def from_entity(cls, i) -> "QualityExceptionQueueItemResponse":
        return cls(
            id=i.id,
            quality_check_job_id=i.quality_check_job_id,
            dataset_id=i.dataset_id,
            row_index=i.row_index,
            standardized_fields=i.standardized_fields,
            failed_rules=i.failed_rules,
            status=i.status,
            created_at=i.created_at,
        )