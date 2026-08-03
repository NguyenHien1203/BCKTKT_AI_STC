"""SqlAlchemy repository implementations cho data-quality-service — UC-029."""
import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    MappedStandardRecord,
    MappingJob,
    MappingRejection,
    MappingRule,
    OcrExtractedTable,
    OcrJob,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
    UnmappedQueueItem,
)
from app.domain.repositories import (
    MappedStandardRecordRepository,
    MappingJobRepository,
    MappingRejectionRepository,
    MappingRuleRepository,
    OcrExtractedTableRepository,
    OcrJobRepository,
    ParsedRecordRepository,
    ParsingJobRepository,
    ParsingRowErrorRepository,
    StgStructuredRowRepository,
    UnmappedQueueRepository,
)
from app.infrastructure.db.models import (
    MappedStandardRecordModel,
    MappingJobModel,
    MappingRejectionModel,
    MappingRuleModel,
    OcrExtractedTableModel,
    OcrJobModel,
    ParsedStructuredRecordModel,
    ParsingJobModel,
    ParsingRowErrorModel,
    StgStructuredRowModel,
    UnmappedQueueItemModel,
)


def _job_to_entity(m: ParsingJobModel) -> ParsingJob:
    job = ParsingJob(
        id=m.id,
        dataset_id=m.dataset_id,
        source_format=m.source_format,
        raw_object_key=m.raw_object_key,
        schema_fields=json.loads(m.schema_fields_json or "[]"),
        field_mapping=json.loads(m.field_mapping_json or "{}"),
        ingestion_run_id=m.ingestion_run_id,
        data_source_id=m.data_source_id,
        status=m.status,
        records_read=m.records_read,
        records_parsed=m.records_parsed,
        records_failed=m.records_failed,
        mapping_event_published=m.mapping_event_published,
        log_entries=json.loads(m.log_entries_json or "[]"),
        error_message=m.error_message,
        received_at=m.received_at,
        completed_at=m.completed_at,
    )
    return job


class SqlAlchemyParsingJobRepository(ParsingJobRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, job: ParsingJob) -> ParsingJob:
        model = ParsingJobModel(
            dataset_id=job.dataset_id,
            ingestion_run_id=job.ingestion_run_id,
            data_source_id=job.data_source_id,
            source_format=job.source_format,
            raw_object_key=job.raw_object_key,
            schema_fields_json=json.dumps(job.schema_fields, ensure_ascii=False),
            field_mapping_json=json.dumps(job.field_mapping, ensure_ascii=False),
            status=job.status,
            records_read=job.records_read,
            records_parsed=job.records_parsed,
            records_failed=job.records_failed,
            mapping_event_published=job.mapping_event_published,
            log_entries_json=json.dumps(job.log_entries, ensure_ascii=False),
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        job.id = model.id
        return job

    def update(self, job: ParsingJob) -> ParsingJob:
        model = self._db.get(ParsingJobModel, job.id)
        if model is None:
            return job
        model.status = job.status
        model.records_read = job.records_read
        model.records_parsed = job.records_parsed
        model.records_failed = job.records_failed
        model.mapping_event_published = job.mapping_event_published
        model.log_entries_json = json.dumps(job.log_entries, ensure_ascii=False)
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return job

    def get_by_id(self, parsing_job_id: int) -> Optional[ParsingJob]:
        model = self._db.get(ParsingJobModel, parsing_job_id)
        return _job_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
        ingestion_run_id: Optional[int] = None,
    ) -> List[ParsingJob]:
        stmt = select(ParsingJobModel)
        if dataset_id is not None:
            stmt = stmt.where(ParsingJobModel.dataset_id == dataset_id)
        if status is not None:
            stmt = stmt.where(ParsingJobModel.status == status)
        if ingestion_run_id is not None:
            stmt = stmt.where(ParsingJobModel.ingestion_run_id == ingestion_run_id)
        stmt = stmt.order_by(ParsingJobModel.id.desc())
        return [_job_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyStgStructuredRowRepository(StgStructuredRowRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, parsing_job_id: int, raw_rows: List[dict]) -> None:
        for idx, row in enumerate(raw_rows):
            self._db.add(
                StgStructuredRowModel(
                    parsing_job_id=parsing_job_id,
                    row_index=idx,
                    raw_data_json=json.dumps(row, ensure_ascii=False, default=str),
                )
            )
        self._db.commit()

    def list_for_job(self, parsing_job_id: int) -> List[dict]:
        stmt = (
            select(StgStructuredRowModel)
            .where(StgStructuredRowModel.parsing_job_id == parsing_job_id)
            .order_by(StgStructuredRowModel.row_index)
        )
        return [json.loads(m.raw_data_json) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyParsedRecordRepository(ParsedRecordRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        for rec in records:
            model = ParsedStructuredRecordModel(
                parsing_job_id=rec.parsing_job_id,
                row_index=rec.row_index,
                mapped_fields_json=json.dumps(rec.mapped_fields, ensure_ascii=False, default=str),
                has_error=rec.has_error,
            )
            self._db.add(model)
        self._db.commit()
        return records

    def list_for_job(self, parsing_job_id: int) -> List[ParsedRecord]:
        stmt = (
            select(ParsedStructuredRecordModel)
            .where(ParsedStructuredRecordModel.parsing_job_id == parsing_job_id)
            .order_by(ParsedStructuredRecordModel.row_index)
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                ParsedRecord(
                    id=m.id,
                    parsing_job_id=m.parsing_job_id,
                    row_index=m.row_index,
                    mapped_fields=json.loads(m.mapped_fields_json),
                    has_error=m.has_error,
                )
            )
        return result


class SqlAlchemyParsingRowErrorRepository(ParsingRowErrorRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, errors: List[ParsingRowError]) -> List[ParsingRowError]:
        for err in errors:
            model = ParsingRowErrorModel(
                parsing_job_id=err.parsing_job_id,
                row_index=err.row_index,
                field_name=err.field_name,
                message=err.message,
            )
            self._db.add(model)
        self._db.commit()
        return errors

    def list_for_job(self, parsing_job_id: int) -> List[ParsingRowError]:
        stmt = (
            select(ParsingRowErrorModel)
            .where(ParsingRowErrorModel.parsing_job_id == parsing_job_id)
            .order_by(ParsingRowErrorModel.row_index)
        )
        return [
            ParsingRowError(
                id=m.id,
                parsing_job_id=m.parsing_job_id,
                row_index=m.row_index,
                field_name=m.field_name,
                message=m.message,
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


# ---------- UC-030: Phân tích PDF/bản quét + OCR ----------


def _ocr_job_to_entity(m: OcrJobModel) -> OcrJob:
    return OcrJob(
        id=m.id,
        raw_object_key=m.raw_object_key,
        van_ban_intake_id=m.van_ban_intake_id,
        data_source_id=m.data_source_id,
        so_ky_hieu=m.so_ky_hieu,
        engine_requested=m.engine_requested,
        engine_used=m.engine_used,
        status=m.status,
        pages_processed=m.pages_processed,
        extracted_text=m.extracted_text,
        table_count=m.table_count,
        ocr_completed_published=m.ocr_completed_published,
        parsing_requested_published=m.parsing_requested_published,
        log_entries=json.loads(m.log_entries_json or "[]"),
        error_message=m.error_message,
        received_at=m.received_at,
        completed_at=m.completed_at,
    )


class SqlAlchemyOcrJobRepository(OcrJobRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, job: OcrJob) -> OcrJob:
        model = OcrJobModel(
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
            log_entries_json=json.dumps(job.log_entries, ensure_ascii=False),
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        job.id = model.id
        return job

    def update(self, job: OcrJob) -> OcrJob:
        model = self._db.get(OcrJobModel, job.id)
        if model is None:
            return job
        model.engine_used = job.engine_used
        model.status = job.status
        model.pages_processed = job.pages_processed
        model.extracted_text = job.extracted_text
        model.table_count = job.table_count
        model.ocr_completed_published = job.ocr_completed_published
        model.parsing_requested_published = job.parsing_requested_published
        model.log_entries_json = json.dumps(job.log_entries, ensure_ascii=False)
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return job

    def get_by_id(self, ocr_job_id: int) -> Optional[OcrJob]:
        model = self._db.get(OcrJobModel, ocr_job_id)
        return _ocr_job_to_entity(model) if model else None

    def list(
        self,
        data_source_id: Optional[int] = None,
        status: Optional[str] = None,
        van_ban_intake_id: Optional[int] = None,
    ) -> List[OcrJob]:
        stmt = select(OcrJobModel)
        if data_source_id is not None:
            stmt = stmt.where(OcrJobModel.data_source_id == data_source_id)
        if status is not None:
            stmt = stmt.where(OcrJobModel.status == status)
        if van_ban_intake_id is not None:
            stmt = stmt.where(OcrJobModel.van_ban_intake_id == van_ban_intake_id)
        stmt = stmt.order_by(OcrJobModel.id.desc())
        return [_ocr_job_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyOcrExtractedTableRepository(OcrExtractedTableRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, tables: List[OcrExtractedTable]) -> List[OcrExtractedTable]:
        for t in tables:
            model = OcrExtractedTableModel(
                ocr_job_id=t.ocr_job_id,
                table_index=t.table_index,
                page_number=t.page_number,
                rows_json=json.dumps(t.rows, ensure_ascii=False, default=str),
            )
            self._db.add(model)
        self._db.commit()
        return tables

    def list_for_job(self, ocr_job_id: int) -> List[OcrExtractedTable]:
        stmt = (
            select(OcrExtractedTableModel)
            .where(OcrExtractedTableModel.ocr_job_id == ocr_job_id)
            .order_by(OcrExtractedTableModel.table_index)
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                OcrExtractedTable(
                    id=m.id,
                    ocr_job_id=m.ocr_job_id,
                    table_index=m.table_index,
                    page_number=m.page_number,
                    rows=json.loads(m.rows_json),
                )
            )
        return result

# ---------- UC-031: Ánh xạ trường sang dạng chuẩn ----------


def _rule_to_entity(m: MappingRuleModel) -> MappingRule:
    return MappingRule(
        id=m.id,
        field_name=m.field_name,
        version=m.version,
        rule_type=m.rule_type,
        dataset_id=m.dataset_id,
        catalog_map=json.loads(m.catalog_map_json or "{}"),
        normalize_case=m.normalize_case,
        is_active=m.is_active,
        created_at=m.created_at,
    )


class SqlAlchemyMappingRuleRepository(MappingRuleRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, rule: MappingRule) -> MappingRule:
        model = MappingRuleModel(
            dataset_id=rule.dataset_id,
            field_name=rule.field_name,
            version=rule.version,
            rule_type=rule.rule_type,
            catalog_map_json=json.dumps(rule.catalog_map, ensure_ascii=False),
            normalize_case=rule.normalize_case,
            is_active=rule.is_active,
            created_at=rule.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        rule.id = model.id
        return rule

    def get_by_id(self, rule_id: int) -> Optional[MappingRule]:
        model = self._db.get(MappingRuleModel, rule_id)
        return _rule_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[MappingRule]:
        stmt = select(MappingRuleModel)
        if dataset_id is not None:
            stmt = stmt.where(MappingRuleModel.dataset_id == dataset_id)
        if field_name is not None:
            stmt = stmt.where(MappingRuleModel.field_name == field_name)
        if is_active is not None:
            stmt = stmt.where(MappingRuleModel.is_active == is_active)
        stmt = stmt.order_by(MappingRuleModel.field_name, MappingRuleModel.version.desc())
        return [_rule_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def get_active_rules_for_dataset(self, dataset_id: int) -> Dict[str, MappingRule]:
        stmt = (
            select(MappingRuleModel)
            .where(MappingRuleModel.is_active.is_(True))
            .where(
                (MappingRuleModel.dataset_id == dataset_id)
                | (MappingRuleModel.dataset_id.is_(None))
            )
            .order_by(MappingRuleModel.version.asc())
        )
        rules_by_field: Dict[str, MappingRule] = {}
        specific_fields: set = set()
        for m in self._db.execute(stmt).scalars().all():
            entity = _rule_to_entity(m)
            is_specific = entity.dataset_id == dataset_id
            existing = rules_by_field.get(entity.field_name)
            if existing is None:
                rules_by_field[entity.field_name] = entity
                if is_specific:
                    specific_fields.add(entity.field_name)
                continue
            already_specific = entity.field_name in specific_fields
            if is_specific and not already_specific:
                # Quy tắc gắn dataset cụ thể luôn được ưu tiên hơn quy tắc chung.
                rules_by_field[entity.field_name] = entity
                specific_fields.add(entity.field_name)
            elif is_specific == already_specific:
                # Cùng phạm vi (đều chung hoặc đều gắn dataset) -> lấy version lớn nhất
                # (đã order_by version.asc() nên bản ghi sau luôn version >= bản ghi trước).
                rules_by_field[entity.field_name] = entity
        return rules_by_field


def _mapping_job_to_entity(m: MappingJobModel) -> MappingJob:
    return MappingJob(
        id=m.id,
        parsing_job_id=m.parsing_job_id,
        dataset_id=m.dataset_id,
        status=m.status,
        records_total=m.records_total,
        records_mapped=m.records_mapped,
        records_rejected=m.records_rejected,
        unmapped_values_count=m.unmapped_values_count,
        log_entries=json.loads(m.log_entries_json or "[]"),
        error_message=m.error_message,
        received_at=m.received_at,
        completed_at=m.completed_at,
    )


class SqlAlchemyMappingJobRepository(MappingJobRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, job: MappingJob) -> MappingJob:
        model = MappingJobModel(
            parsing_job_id=job.parsing_job_id,
            dataset_id=job.dataset_id,
            status=job.status,
            records_total=job.records_total,
            records_mapped=job.records_mapped,
            records_rejected=job.records_rejected,
            unmapped_values_count=job.unmapped_values_count,
            log_entries_json=json.dumps(job.log_entries, ensure_ascii=False),
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        job.id = model.id
        return job

    def update(self, job: MappingJob) -> MappingJob:
        model = self._db.get(MappingJobModel, job.id)
        if model is None:
            return job
        model.status = job.status
        model.records_total = job.records_total
        model.records_mapped = job.records_mapped
        model.records_rejected = job.records_rejected
        model.unmapped_values_count = job.unmapped_values_count
        model.log_entries_json = json.dumps(job.log_entries, ensure_ascii=False)
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return job

    def get_by_id(self, mapping_job_id: int) -> Optional[MappingJob]:
        model = self._db.get(MappingJobModel, mapping_job_id)
        return _mapping_job_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        parsing_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[MappingJob]:
        stmt = select(MappingJobModel)
        if dataset_id is not None:
            stmt = stmt.where(MappingJobModel.dataset_id == dataset_id)
        if parsing_job_id is not None:
            stmt = stmt.where(MappingJobModel.parsing_job_id == parsing_job_id)
        if status is not None:
            stmt = stmt.where(MappingJobModel.status == status)
        stmt = stmt.order_by(MappingJobModel.id.desc())
        return [_mapping_job_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyMappingRejectionRepository(MappingRejectionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, rejections: List[MappingRejection]) -> List[MappingRejection]:
        for r in rejections:
            self._db.add(
                MappingRejectionModel(
                    mapping_job_id=r.mapping_job_id,
                    row_index=r.row_index,
                    field_name=r.field_name,
                    reason=r.reason,
                    rejected_at=r.rejected_at,
                )
            )
        self._db.commit()
        return rejections

    def list_for_job(self, mapping_job_id: int) -> List[MappingRejection]:
        stmt = (
            select(MappingRejectionModel)
            .where(MappingRejectionModel.mapping_job_id == mapping_job_id)
            .order_by(MappingRejectionModel.row_index)
        )
        return [
            MappingRejection(
                id=m.id,
                mapping_job_id=m.mapping_job_id,
                row_index=m.row_index,
                field_name=m.field_name,
                reason=m.reason,
                rejected_at=m.rejected_at,
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


def _unmapped_item_to_entity(m: UnmappedQueueItemModel) -> UnmappedQueueItem:
    return UnmappedQueueItem(
        id=m.id,
        mapping_job_id=m.mapping_job_id,
        dataset_id=m.dataset_id,
        row_index=m.row_index,
        field_name=m.field_name,
        raw_value=m.raw_value,
        status=m.status,
        resolution_action=m.resolution_action,
        resolved_value=m.resolved_value,
        resolution_reason=m.resolution_reason,
        resolved_at=m.resolved_at,
        created_at=m.created_at,
    )


class SqlAlchemyUnmappedQueueRepository(UnmappedQueueRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, items: List[UnmappedQueueItem]) -> List[UnmappedQueueItem]:
        for it in items:
            self._db.add(
                UnmappedQueueItemModel(
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
            )
        self._db.commit()
        return items

    def list_for_job(self, mapping_job_id: int) -> List[UnmappedQueueItem]:
        stmt = (
            select(UnmappedQueueItemModel)
            .where(UnmappedQueueItemModel.mapping_job_id == mapping_job_id)
            .order_by(UnmappedQueueItemModel.row_index)
        )
        return [_unmapped_item_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def get_by_id(self, item_id: int) -> Optional[UnmappedQueueItem]:
        model = self._db.get(UnmappedQueueItemModel, item_id)
        return _unmapped_item_to_entity(model) if model else None

    def update(self, item: UnmappedQueueItem) -> UnmappedQueueItem:
        model = self._db.get(UnmappedQueueItemModel, item.id)
        if model is None:
            return item
        model.status = item.status
        model.resolution_action = item.resolution_action
        model.resolved_value = item.resolved_value
        model.resolution_reason = item.resolution_reason
        model.resolved_at = item.resolved_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return item

    def list_queue(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[UnmappedQueueItem]:
        stmt = select(UnmappedQueueItemModel)
        if dataset_id is not None:
            stmt = stmt.where(UnmappedQueueItemModel.dataset_id == dataset_id)
        if field_name is not None:
            stmt = stmt.where(UnmappedQueueItemModel.field_name == field_name)
        if status is not None:
            stmt = stmt.where(UnmappedQueueItemModel.status == status)
        stmt = stmt.order_by(UnmappedQueueItemModel.id.asc())
        return [_unmapped_item_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def find_similar_pending(
        self,
        dataset_id: int,
        field_name: str,
        raw_value: str,
        exclude_id: Optional[int] = None,
    ) -> List[UnmappedQueueItem]:
        key = raw_value.strip().upper()
        stmt = (
            select(UnmappedQueueItemModel)
            .where(UnmappedQueueItemModel.dataset_id == dataset_id)
            .where(UnmappedQueueItemModel.field_name == field_name)
            .where(UnmappedQueueItemModel.status == "PENDING")
        )
        if exclude_id is not None:
            stmt = stmt.where(UnmappedQueueItemModel.id != exclude_id)
        result = []
        for m in self._db.execute(stmt).scalars().all():
            if m.raw_value.strip().upper() == key:
                result.append(_unmapped_item_to_entity(m))
        return result


class SqlAlchemyMappedStandardRecordRepository(MappedStandardRecordRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(self, records: List[MappedStandardRecord]) -> List[MappedStandardRecord]:
        for rec in records:
            self._db.add(
                MappedStandardRecordModel(
                    mapping_job_id=rec.mapping_job_id,
                    row_index=rec.row_index,
                    standardized_fields_json=json.dumps(
                        rec.standardized_fields, ensure_ascii=False, default=str
                    ),
                )
            )
        self._db.commit()
        return records

    def list_for_job(self, mapping_job_id: int) -> List[MappedStandardRecord]:
        stmt = (
            select(MappedStandardRecordModel)
            .where(MappedStandardRecordModel.mapping_job_id == mapping_job_id)
            .order_by(MappedStandardRecordModel.row_index)
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                MappedStandardRecord(
                    id=m.id,
                    mapping_job_id=m.mapping_job_id,
                    row_index=m.row_index,
                    standardized_fields=json.loads(m.standardized_fields_json),
                )
            )
        return result