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
            created_at=it.created_at,
        )


class MappedStandardRecordResponse(BaseModel):
    row_index: int
    standardized_fields: Dict[str, Any]

    @classmethod
    def from_entity(cls, rec) -> "MappedStandardRecordResponse":
        return cls(row_index=rec.row_index, standardized_fields=rec.standardized_fields)