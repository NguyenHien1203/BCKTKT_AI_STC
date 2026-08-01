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