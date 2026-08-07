"""SqlAlchemy repository implementations cho data-quality-service — UC-029."""
import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    AssetDepreciationRate,
    AssetGroupCatalogEntry,
    AssetGroupCatalogVersion,
    BudgetItemCatalogEntry,
    BudgetItemCatalogVersion,
    BudgetItemChangeRequest,
    CatalogChangeAuditLog,
    CatalogChangeRequest,
    CatalogEntry,
    CatalogEntryVersion,
    CuratedBatchSummary,
    CuratedDatasetFreshness,
    CuratedDmRecord,
    CuratedPublishJob,
    DatasetMetadataEntry,
    DatasetMetadataVersion,
    MappedStandardRecord,
    MappingJob,
    MappingRejection,
    MappingRule,
    OcrExtractedTable,
    OcrJob,
    OrgUnitCatalogEntry,
    OrgUnitCatalogVersion,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
    QualityCheckJob,
    QualityCheckRuleResult,
    QualityExceptionQueueItem,
    QualityPublishedRecord,
    QualityRule,
    QualityRuleVersion,
    QualityScoreConfig,
    QualityScoreConfigVersion,
    SemanticIndicator,
    SemanticIndicatorVersion,
    IndicatorTestRun,
    IndicatorAuditLog,
    IndicatorApprovalDecision,
    UnmappedQueueItem,
)
from app.domain.repositories import (
    AssetDepreciationRateRepository,
    AssetGroupCatalogRepository,
    AssetGroupCatalogVersionRepository,
    BudgetItemCatalogRepository,
    BudgetItemCatalogVersionRepository,
    BudgetItemChangeRequestRepository,
    CatalogChangeAuditLogRepository,
    CatalogChangeRequestRepository,
    CatalogEntryRepository,
    CatalogEntryVersionRepository,
    CuratedBatchSummaryRepository,
    CuratedDatasetFreshnessRepository,
    CuratedDmRecordRepository,
    CuratedPublishJobRepository,
    DatasetMetadataRepository,
    DatasetMetadataVersionRepository,
    MappedStandardRecordRepository,
    MappingJobRepository,
    MappingRejectionRepository,
    MappingRuleRepository,
    OcrExtractedTableRepository,
    OcrJobRepository,
    OrgUnitCatalogRepository,
    OrgUnitCatalogVersionRepository,
    ParsedRecordRepository,
    ParsingJobRepository,
    ParsingRowErrorRepository,
    QualityCheckJobRepository,
    QualityCheckRuleResultRepository,
    QualityExceptionQueueRepository,
    QualityPublishedRecordRepository,
    QualityRuleRepository,
    QualityRuleVersionRepository,
    QualityScoreConfigRepository,
    QualityScoreConfigVersionRepository,
    SemanticIndicatorRepository,
    SemanticIndicatorVersionRepository,
    IndicatorTestRunRepository,
    IndicatorAuditLogRepository,
    IndicatorApprovalDecisionRepository,
    StgStructuredRowRepository,
    UnmappedQueueRepository,
)
from app.infrastructure.db.models import (
    AssetDepreciationRateModel,
    AssetGroupCatalogModel,
    AssetGroupCatalogVersionModel,
    BudgetItemCatalogModel,
    BudgetItemCatalogVersionModel,
    BudgetItemChangeRequestModel,
    CatalogChangeAuditLogModel,
    CatalogChangeRequestModel,
    CatalogEntryModel,
    CatalogEntryVersionModel,
    CuratedBatchSummaryModel,
    CuratedDatasetFreshnessModel,
    CuratedDmRecordModel,
    CuratedPublishJobModel,
    DatasetMetadataModel,
    DatasetMetadataVersionModel,
    MappedStandardRecordModel,
    MappingJobModel,
    MappingRejectionModel,
    MappingRuleModel,
    OcrExtractedTableModel,
    OcrJobModel,
    OrgUnitCatalogModel,
    OrgUnitCatalogVersionModel,
    ParsedStructuredRecordModel,
    ParsingJobModel,
    ParsingRowErrorModel,
    QualityCheckJobModel,
    QualityCheckRuleResultModel,
    QualityExceptionQueueItemModel,
    QualityPublishedRecordModel,
    QualityRuleModel,
    QualityRuleVersionModel,
    QualityScoreConfigModel,
    QualityScoreConfigVersionModel,
    SemanticIndicatorModel,
    SemanticIndicatorVersionModel,
    IndicatorTestRunModel,
    IndicatorAuditLogModel,
    IndicatorApprovalDecisionModel,
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

def _org_unit_to_entity(m: OrgUnitCatalogModel) -> OrgUnitCatalogEntry:
    return OrgUnitCatalogEntry(
        id=m.id,
        code=m.code,
        name=m.name,
        unit_type=m.unit_type,
        parent_id=m.parent_id,
        status=m.status,
        version=m.version,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        lifecycle_action=m.lifecycle_action,
        lifecycle_note=m.lifecycle_note,
        split_from_id=m.split_from_id,
        merged_from_ids=json.loads(m.merged_from_ids_json or "[]"),
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyOrgUnitCatalogRepository(OrgUnitCatalogRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, unit: OrgUnitCatalogEntry) -> OrgUnitCatalogEntry:
        model = OrgUnitCatalogModel(
            code=unit.code,
            name=unit.name,
            unit_type=unit.unit_type,
            parent_id=unit.parent_id,
            status=unit.status,
            version=unit.version,
            effective_from=unit.effective_from,
            effective_to=unit.effective_to,
            lifecycle_action=unit.lifecycle_action,
            lifecycle_note=unit.lifecycle_note,
            split_from_id=unit.split_from_id,
            merged_from_ids_json=json.dumps(unit.merged_from_ids),
            created_at=unit.created_at,
            updated_at=unit.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        unit.id = model.id
        return unit

    def update(self, unit: OrgUnitCatalogEntry) -> OrgUnitCatalogEntry:
        model = self._db.get(OrgUnitCatalogModel, unit.id)
        if model is None:
            return unit
        model.code = unit.code
        model.name = unit.name
        model.unit_type = unit.unit_type
        model.parent_id = unit.parent_id
        model.status = unit.status
        model.version = unit.version
        model.effective_from = unit.effective_from
        model.effective_to = unit.effective_to
        model.lifecycle_action = unit.lifecycle_action
        model.lifecycle_note = unit.lifecycle_note
        model.split_from_id = unit.split_from_id
        model.merged_from_ids_json = json.dumps(unit.merged_from_ids)
        model.updated_at = unit.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return unit

    def get_by_id(self, unit_id: int) -> Optional[OrgUnitCatalogEntry]:
        model = self._db.get(OrgUnitCatalogModel, unit_id)
        return _org_unit_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[OrgUnitCatalogEntry]:
        stmt = select(OrgUnitCatalogModel).where(OrgUnitCatalogModel.code == code)
        model = self._db.execute(stmt).scalars().first()
        return _org_unit_to_entity(model) if model else None

    def list(
        self,
        parent_id: Optional[int] = "__unset__",
        unit_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[OrgUnitCatalogEntry]:
        stmt = select(OrgUnitCatalogModel)
        if parent_id != "__unset__":
            stmt = stmt.where(OrgUnitCatalogModel.parent_id == parent_id)
        if unit_type is not None:
            stmt = stmt.where(OrgUnitCatalogModel.unit_type == unit_type)
        if status is not None:
            stmt = stmt.where(OrgUnitCatalogModel.status == status)
        stmt = stmt.order_by(OrgUnitCatalogModel.code.asc())
        return [_org_unit_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def list_all(self) -> List[OrgUnitCatalogEntry]:
        stmt = select(OrgUnitCatalogModel).order_by(OrgUnitCatalogModel.code.asc())
        return [_org_unit_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyOrgUnitCatalogVersionRepository(OrgUnitCatalogVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: OrgUnitCatalogVersion) -> OrgUnitCatalogVersion:
        model = OrgUnitCatalogVersionModel(
            unit_id=version.unit_id,
            version=version.version,
            code=version.code,
            name=version.name,
            unit_type=version.unit_type,
            parent_id=version.parent_id,
            status=version.status,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_unit(self, unit_id: int) -> List[OrgUnitCatalogVersion]:
        stmt = (
            select(OrgUnitCatalogVersionModel)
            .where(OrgUnitCatalogVersionModel.unit_id == unit_id)
            .order_by(OrgUnitCatalogVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                OrgUnitCatalogVersion(
                    id=m.id,
                    unit_id=m.unit_id,
                    version=m.version,
                    code=m.code,
                    name=m.name,
                    unit_type=m.unit_type,
                    parent_id=m.parent_id,
                    status=m.status,
                    effective_from=m.effective_from,
                    effective_to=m.effective_to,
                    change_note=m.change_note,
                    changed_at=m.changed_at,
                )
            )
        return result

def _budget_item_to_entity(m: BudgetItemCatalogModel) -> BudgetItemCatalogEntry:
    return BudgetItemCatalogEntry(
        id=m.id,
        code=m.code,
        name=m.name,
        level=m.level,
        budget_year=m.budget_year,
        parent_id=m.parent_id,
        status=m.status,
        version=m.version,
        is_sensitive=m.is_sensitive,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyBudgetItemCatalogRepository(BudgetItemCatalogRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, item: BudgetItemCatalogEntry) -> BudgetItemCatalogEntry:
        model = BudgetItemCatalogModel(
            code=item.code,
            name=item.name,
            level=item.level,
            budget_year=item.budget_year,
            parent_id=item.parent_id,
            status=item.status,
            version=item.version,
            is_sensitive=item.is_sensitive,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        item.id = model.id
        return item

    def update(self, item: BudgetItemCatalogEntry) -> BudgetItemCatalogEntry:
        model = self._db.get(BudgetItemCatalogModel, item.id)
        if model is None:
            return item
        model.code = item.code
        model.name = item.name
        model.level = item.level
        model.budget_year = item.budget_year
        model.parent_id = item.parent_id
        model.status = item.status
        model.version = item.version
        model.is_sensitive = item.is_sensitive
        model.effective_from = item.effective_from
        model.effective_to = item.effective_to
        model.updated_at = item.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return item

    def get_by_id(self, item_id: int) -> Optional[BudgetItemCatalogEntry]:
        model = self._db.get(BudgetItemCatalogModel, item_id)
        return _budget_item_to_entity(model) if model else None

    def get_by_code(self, code: str, budget_year: int) -> Optional[BudgetItemCatalogEntry]:
        stmt = select(BudgetItemCatalogModel).where(
            BudgetItemCatalogModel.code == code,
            BudgetItemCatalogModel.budget_year == budget_year,
        )
        model = self._db.execute(stmt).scalars().first()
        return _budget_item_to_entity(model) if model else None

    def list(
        self,
        budget_year: Optional[int] = None,
        parent_id: Optional[int] = "__unset__",
        level: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BudgetItemCatalogEntry]:
        stmt = select(BudgetItemCatalogModel)
        if budget_year is not None:
            stmt = stmt.where(BudgetItemCatalogModel.budget_year == budget_year)
        if parent_id != "__unset__":
            stmt = stmt.where(BudgetItemCatalogModel.parent_id == parent_id)
        if level is not None:
            stmt = stmt.where(BudgetItemCatalogModel.level == level)
        if status is not None:
            stmt = stmt.where(BudgetItemCatalogModel.status == status)
        stmt = stmt.order_by(BudgetItemCatalogModel.code.asc())
        return [_budget_item_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def list_by_year(self, budget_year: int) -> List[BudgetItemCatalogEntry]:
        stmt = (
            select(BudgetItemCatalogModel)
            .where(BudgetItemCatalogModel.budget_year == budget_year)
            .order_by(BudgetItemCatalogModel.code.asc())
        )
        return [_budget_item_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyBudgetItemCatalogVersionRepository(BudgetItemCatalogVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: BudgetItemCatalogVersion) -> BudgetItemCatalogVersion:
        model = BudgetItemCatalogVersionModel(
            item_id=version.item_id,
            budget_year=version.budget_year,
            version=version.version,
            code=version.code,
            name=version.name,
            level=version.level,
            parent_id=version.parent_id,
            status=version.status,
            is_sensitive=version.is_sensitive,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_item(self, item_id: int) -> List[BudgetItemCatalogVersion]:
        stmt = (
            select(BudgetItemCatalogVersionModel)
            .where(BudgetItemCatalogVersionModel.item_id == item_id)
            .order_by(BudgetItemCatalogVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                BudgetItemCatalogVersion(
                    id=m.id,
                    item_id=m.item_id,
                    budget_year=m.budget_year,
                    version=m.version,
                    code=m.code,
                    name=m.name,
                    level=m.level,
                    parent_id=m.parent_id,
                    status=m.status,
                    is_sensitive=m.is_sensitive,
                    change_note=m.change_note,
                    changed_at=m.changed_at,
                )
            )
        return result


class SqlAlchemyBudgetItemChangeRequestRepository(BudgetItemChangeRequestRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, request: BudgetItemChangeRequest) -> BudgetItemChangeRequest:
        model = BudgetItemChangeRequestModel(
            item_id=request.item_id,
            budget_year=request.budget_year,
            requested_by=request.requested_by,
            reason=request.reason,
            proposed_name=request.proposed_name,
            proposed_status=request.proposed_status,
            proposed_is_sensitive=request.proposed_is_sensitive,
            status=request.status,
            reviewed_by=request.reviewed_by,
            review_note=request.review_note,
            reviewed_at=request.reviewed_at,
            created_at=request.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        request.id = model.id
        return request

    def update(self, request: BudgetItemChangeRequest) -> BudgetItemChangeRequest:
        model = self._db.get(BudgetItemChangeRequestModel, request.id)
        if model is None:
            return request
        model.status = request.status
        model.reviewed_by = request.reviewed_by
        model.review_note = request.review_note
        model.reviewed_at = request.reviewed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return request

    def get_by_id(self, request_id: int) -> Optional[BudgetItemChangeRequest]:
        model = self._db.get(BudgetItemChangeRequestModel, request_id)
        return _budget_item_change_request_to_entity(model) if model else None

    def list(
        self,
        item_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[BudgetItemChangeRequest]:
        stmt = select(BudgetItemChangeRequestModel)
        if item_id is not None:
            stmt = stmt.where(BudgetItemChangeRequestModel.item_id == item_id)
        if status is not None:
            stmt = stmt.where(BudgetItemChangeRequestModel.status == status)
        stmt = stmt.order_by(BudgetItemChangeRequestModel.created_at.desc())
        return [
            _budget_item_change_request_to_entity(m)
            for m in self._db.execute(stmt).scalars().all()
        ]


def _budget_item_change_request_to_entity(
    m: BudgetItemChangeRequestModel,
) -> BudgetItemChangeRequest:
    return BudgetItemChangeRequest(
        id=m.id,
        item_id=m.item_id,
        budget_year=m.budget_year,
        requested_by=m.requested_by,
        reason=m.reason,
        proposed_name=m.proposed_name,
        proposed_status=m.proposed_status,
        proposed_is_sensitive=m.proposed_is_sensitive,
        status=m.status,
        reviewed_by=m.reviewed_by,
        review_note=m.review_note,
        reviewed_at=m.reviewed_at,
        created_at=m.created_at,
    )

# ---------- UC-035: Quản lý danh mục nhóm tài sản ----------


def _asset_group_to_entity(m: AssetGroupCatalogModel) -> AssetGroupCatalogEntry:
    return AssetGroupCatalogEntry(
        id=m.id,
        code=m.code,
        name=m.name,
        regulation=m.regulation,
        useful_life_years=m.useful_life_years,
        status=m.status,
        version=m.version,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        note=m.note,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyAssetGroupCatalogRepository(AssetGroupCatalogRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, group: AssetGroupCatalogEntry) -> AssetGroupCatalogEntry:
        model = AssetGroupCatalogModel(
            code=group.code,
            name=group.name,
            regulation=group.regulation,
            useful_life_years=group.useful_life_years,
            status=group.status,
            version=group.version,
            effective_from=group.effective_from,
            effective_to=group.effective_to,
            note=group.note,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        group.id = model.id
        return group

    def update(self, group: AssetGroupCatalogEntry) -> AssetGroupCatalogEntry:
        model = self._db.get(AssetGroupCatalogModel, group.id)
        if model is None:
            return group
        model.code = group.code
        model.name = group.name
        model.regulation = group.regulation
        model.useful_life_years = group.useful_life_years
        model.status = group.status
        model.version = group.version
        model.effective_from = group.effective_from
        model.effective_to = group.effective_to
        model.note = group.note
        model.updated_at = group.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return group

    def get_by_id(self, group_id: int) -> Optional[AssetGroupCatalogEntry]:
        model = self._db.get(AssetGroupCatalogModel, group_id)
        return _asset_group_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[AssetGroupCatalogEntry]:
        stmt = select(AssetGroupCatalogModel).where(AssetGroupCatalogModel.code == code)
        model = self._db.execute(stmt).scalars().first()
        return _asset_group_to_entity(model) if model else None

    def list(
        self,
        regulation: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AssetGroupCatalogEntry]:
        stmt = select(AssetGroupCatalogModel)
        if regulation is not None:
            stmt = stmt.where(AssetGroupCatalogModel.regulation == regulation)
        if status is not None:
            stmt = stmt.where(AssetGroupCatalogModel.status == status)
        stmt = stmt.order_by(AssetGroupCatalogModel.code.asc())
        return [_asset_group_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyAssetGroupCatalogVersionRepository(AssetGroupCatalogVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: AssetGroupCatalogVersion) -> AssetGroupCatalogVersion:
        model = AssetGroupCatalogVersionModel(
            group_id=version.group_id,
            version=version.version,
            code=version.code,
            name=version.name,
            regulation=version.regulation,
            useful_life_years=version.useful_life_years,
            status=version.status,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_group(self, group_id: int) -> List[AssetGroupCatalogVersion]:
        stmt = (
            select(AssetGroupCatalogVersionModel)
            .where(AssetGroupCatalogVersionModel.group_id == group_id)
            .order_by(AssetGroupCatalogVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                AssetGroupCatalogVersion(
                    id=m.id,
                    group_id=m.group_id,
                    version=m.version,
                    code=m.code,
                    name=m.name,
                    regulation=m.regulation,
                    useful_life_years=m.useful_life_years,
                    status=m.status,
                    change_note=m.change_note,
                    changed_at=m.changed_at,
                )
            )
        return result


class SqlAlchemyAssetDepreciationRateRepository(AssetDepreciationRateRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, rate: AssetDepreciationRate) -> AssetDepreciationRate:
        model = AssetDepreciationRateModel(
            asset_group_id=rate.asset_group_id,
            depreciation_rate_percent=rate.depreciation_rate_percent,
            useful_life_years=rate.useful_life_years,
            effective_from=rate.effective_from,
            effective_to=rate.effective_to,
            note=rate.note,
            declared_by=rate.declared_by,
            created_at=rate.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        rate.id = model.id
        return rate

    def get_by_id(self, rate_id: int) -> Optional[AssetDepreciationRate]:
        model = self._db.get(AssetDepreciationRateModel, rate_id)
        return _asset_depreciation_rate_to_entity(model) if model else None

    def list_for_group(self, asset_group_id: int) -> List[AssetDepreciationRate]:
        stmt = (
            select(AssetDepreciationRateModel)
            .where(AssetDepreciationRateModel.asset_group_id == asset_group_id)
            .order_by(AssetDepreciationRateModel.created_at.desc())
        )
        return [
            _asset_depreciation_rate_to_entity(m) for m in self._db.execute(stmt).scalars().all()
        ]


def _asset_depreciation_rate_to_entity(m: AssetDepreciationRateModel) -> AssetDepreciationRate:
    return AssetDepreciationRate(
        id=m.id,
        asset_group_id=m.asset_group_id,
        depreciation_rate_percent=m.depreciation_rate_percent,
        useful_life_years=m.useful_life_years,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        note=m.note,
        declared_by=m.declared_by,
        created_at=m.created_at,
    )

# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


def _catalog_entry_to_entity(m: CatalogEntryModel) -> CatalogEntry:
    return CatalogEntry(
        id=m.id,
        catalog_type=m.catalog_type,
        code=m.code,
        name=m.name,
        unit=m.unit,
        description=m.description,
        status=m.status,
        version=m.version,
        is_sensitive=m.is_sensitive,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyCatalogEntryRepository(CatalogEntryRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, entry: CatalogEntry) -> CatalogEntry:
        model = CatalogEntryModel(
            catalog_type=entry.catalog_type,
            code=entry.code,
            name=entry.name,
            unit=entry.unit,
            description=entry.description,
            status=entry.status,
            version=entry.version,
            is_sensitive=entry.is_sensitive,
            effective_from=entry.effective_from,
            effective_to=entry.effective_to,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        entry.id = model.id
        return entry

    def update(self, entry: CatalogEntry) -> CatalogEntry:
        model = self._db.get(CatalogEntryModel, entry.id)
        if model is None:
            return entry
        model.catalog_type = entry.catalog_type
        model.code = entry.code
        model.name = entry.name
        model.unit = entry.unit
        model.description = entry.description
        model.status = entry.status
        model.version = entry.version
        model.is_sensitive = entry.is_sensitive
        model.effective_from = entry.effective_from
        model.effective_to = entry.effective_to
        model.updated_at = entry.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return entry

    def get_by_id(self, entry_id: int) -> Optional[CatalogEntry]:
        model = self._db.get(CatalogEntryModel, entry_id)
        return _catalog_entry_to_entity(model) if model else None

    def get_by_code(self, code: str, catalog_type: str) -> Optional[CatalogEntry]:
        stmt = select(CatalogEntryModel).where(
            CatalogEntryModel.code == code,
            CatalogEntryModel.catalog_type == catalog_type,
        )
        model = self._db.execute(stmt).scalars().first()
        return _catalog_entry_to_entity(model) if model else None

    def list(
        self,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogEntry]:
        stmt = select(CatalogEntryModel)
        if catalog_type is not None:
            stmt = stmt.where(CatalogEntryModel.catalog_type == catalog_type)
        if status is not None:
            stmt = stmt.where(CatalogEntryModel.status == status)
        stmt = stmt.order_by(CatalogEntryModel.code.asc())
        return [_catalog_entry_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyCatalogEntryVersionRepository(CatalogEntryVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: CatalogEntryVersion) -> CatalogEntryVersion:
        model = CatalogEntryVersionModel(
            entry_id=version.entry_id,
            catalog_type=version.catalog_type,
            version=version.version,
            code=version.code,
            name=version.name,
            unit=version.unit,
            status=version.status,
            is_sensitive=version.is_sensitive,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_entry(self, entry_id: int) -> List[CatalogEntryVersion]:
        stmt = (
            select(CatalogEntryVersionModel)
            .where(CatalogEntryVersionModel.entry_id == entry_id)
            .order_by(CatalogEntryVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                CatalogEntryVersion(
                    id=m.id,
                    entry_id=m.entry_id,
                    catalog_type=m.catalog_type,
                    version=m.version,
                    code=m.code,
                    name=m.name,
                    unit=m.unit,
                    status=m.status,
                    is_sensitive=m.is_sensitive,
                    change_note=m.change_note,
                    changed_at=m.changed_at,
                )
            )
        return result


def _catalog_change_request_to_entity(m: CatalogChangeRequestModel) -> CatalogChangeRequest:
    return CatalogChangeRequest(
        id=m.id,
        entry_id=m.entry_id,
        catalog_type=m.catalog_type,
        requested_by=m.requested_by,
        reason=m.reason,
        proposed_name=m.proposed_name,
        proposed_unit=m.proposed_unit,
        proposed_description=m.proposed_description,
        proposed_status=m.proposed_status,
        proposed_is_sensitive=m.proposed_is_sensitive,
        status=m.status,
        reviewed_by=m.reviewed_by,
        review_note=m.review_note,
        reviewed_at=m.reviewed_at,
        created_at=m.created_at,
    )


class SqlAlchemyCatalogChangeRequestRepository(CatalogChangeRequestRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, request: CatalogChangeRequest) -> CatalogChangeRequest:
        model = CatalogChangeRequestModel(
            entry_id=request.entry_id,
            catalog_type=request.catalog_type,
            requested_by=request.requested_by,
            reason=request.reason,
            proposed_name=request.proposed_name,
            proposed_unit=request.proposed_unit,
            proposed_description=request.proposed_description,
            proposed_status=request.proposed_status,
            proposed_is_sensitive=request.proposed_is_sensitive,
            status=request.status,
            reviewed_by=request.reviewed_by,
            review_note=request.review_note,
            reviewed_at=request.reviewed_at,
            created_at=request.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        request.id = model.id
        return request

    def update(self, request: CatalogChangeRequest) -> CatalogChangeRequest:
        model = self._db.get(CatalogChangeRequestModel, request.id)
        if model is None:
            return request
        model.status = request.status
        model.reviewed_by = request.reviewed_by
        model.review_note = request.review_note
        model.reviewed_at = request.reviewed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return request

    def get_by_id(self, request_id: int) -> Optional[CatalogChangeRequest]:
        model = self._db.get(CatalogChangeRequestModel, request_id)
        return _catalog_change_request_to_entity(model) if model else None

    def list(
        self,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogChangeRequest]:
        stmt = select(CatalogChangeRequestModel)
        if entry_id is not None:
            stmt = stmt.where(CatalogChangeRequestModel.entry_id == entry_id)
        if catalog_type is not None:
            stmt = stmt.where(CatalogChangeRequestModel.catalog_type == catalog_type)
        if status is not None:
            stmt = stmt.where(CatalogChangeRequestModel.status == status)
        stmt = stmt.order_by(CatalogChangeRequestModel.created_at.desc())
        return [
            _catalog_change_request_to_entity(m)
            for m in self._db.execute(stmt).scalars().all()
        ]

def _catalog_change_audit_log_to_entity(m: CatalogChangeAuditLogModel) -> CatalogChangeAuditLog:
    return CatalogChangeAuditLog(
        id=m.id,
        request_id=m.request_id,
        entry_id=m.entry_id,
        catalog_type=m.catalog_type,
        action=m.action,
        decided_by=m.decided_by,
        decision_reason=m.decision_reason,
        diff_snapshot=m.diff_snapshot,
        created_at=m.created_at,
    )


class SqlAlchemyCatalogChangeAuditLogRepository(CatalogChangeAuditLogRepository):
    """UC-037 bước 4: nhật ký append-only (chỉ `add`/`list`, không `update`/`delete`)."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, log: CatalogChangeAuditLog) -> CatalogChangeAuditLog:
        model = CatalogChangeAuditLogModel(
            request_id=log.request_id,
            entry_id=log.entry_id,
            catalog_type=log.catalog_type,
            action=log.action,
            decided_by=log.decided_by,
            decision_reason=log.decision_reason,
            diff_snapshot=log.diff_snapshot,
            created_at=log.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        log.id = model.id
        return log

    def list(
        self,
        request_id: Optional[int] = None,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[CatalogChangeAuditLog]:
        stmt = select(CatalogChangeAuditLogModel)
        if request_id is not None:
            stmt = stmt.where(CatalogChangeAuditLogModel.request_id == request_id)
        if entry_id is not None:
            stmt = stmt.where(CatalogChangeAuditLogModel.entry_id == entry_id)
        if catalog_type is not None:
            stmt = stmt.where(CatalogChangeAuditLogModel.catalog_type == catalog_type)
        if action is not None:
            stmt = stmt.where(CatalogChangeAuditLogModel.action == action)
        stmt = stmt.order_by(CatalogChangeAuditLogModel.created_at.desc())
        return [
            _catalog_change_audit_log_to_entity(m) for m in self._db.execute(stmt).scalars().all()
        ]

# ---------- UC-038: Quản lý quy tắc kiểm tra chất lượng ----------


def _quality_rule_to_entity(m: QualityRuleModel) -> QualityRule:
    return QualityRule(
        id=m.id,
        dataset_id=m.dataset_id,
        field_names=json.loads(m.field_names_json or "[]"),
        rule_type=m.rule_type,
        params=json.loads(m.params_json or "{}"),
        weight=m.weight,
        description=m.description,
        is_active=m.is_active,
        version=m.version,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyQualityRuleRepository(QualityRuleRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, rule: QualityRule) -> QualityRule:
        model = QualityRuleModel(
            dataset_id=rule.dataset_id,
            field_names_json=json.dumps(rule.field_names),
            rule_type=rule.rule_type,
            params_json=json.dumps(rule.params),
            weight=rule.weight,
            description=rule.description,
            is_active=rule.is_active,
            version=rule.version,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        rule.id = model.id
        return rule

    def update(self, rule: QualityRule) -> QualityRule:
        model = self._db.get(QualityRuleModel, rule.id)
        if model is None:
            return rule
        model.dataset_id = rule.dataset_id
        model.field_names_json = json.dumps(rule.field_names)
        model.rule_type = rule.rule_type
        model.params_json = json.dumps(rule.params)
        model.weight = rule.weight
        model.description = rule.description
        model.is_active = rule.is_active
        model.version = rule.version
        model.updated_at = rule.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return rule

    def get_by_id(self, rule_id: int) -> Optional[QualityRule]:
        model = self._db.get(QualityRuleModel, rule_id)
        return _quality_rule_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[QualityRule]:
        stmt = select(QualityRuleModel)
        if dataset_id is not None:
            stmt = stmt.where(QualityRuleModel.dataset_id == dataset_id)
        if rule_type is not None:
            stmt = stmt.where(QualityRuleModel.rule_type == rule_type)
        if is_active is not None:
            stmt = stmt.where(QualityRuleModel.is_active == is_active)
        stmt = stmt.order_by(QualityRuleModel.id.asc())
        return [_quality_rule_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def list_general(self, is_active: Optional[bool] = None) -> List[QualityRule]:
        stmt = select(QualityRuleModel).where(QualityRuleModel.dataset_id.is_(None))
        if is_active is not None:
            stmt = stmt.where(QualityRuleModel.is_active == is_active)
        stmt = stmt.order_by(QualityRuleModel.id.asc())
        return [_quality_rule_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyQualityRuleVersionRepository(QualityRuleVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: QualityRuleVersion) -> QualityRuleVersion:
        model = QualityRuleVersionModel(
            rule_id=version.rule_id,
            version=version.version,
            dataset_id=version.dataset_id,
            field_names_json=json.dumps(version.field_names),
            rule_type=version.rule_type,
            params_json=json.dumps(version.params),
            weight=version.weight,
            is_active=version.is_active,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_rule(self, rule_id: int) -> List[QualityRuleVersion]:
        stmt = (
            select(QualityRuleVersionModel)
            .where(QualityRuleVersionModel.rule_id == rule_id)
            .order_by(QualityRuleVersionModel.version.asc())
        )
        return [
            QualityRuleVersion(
                id=m.id,
                rule_id=m.rule_id,
                version=m.version,
                dataset_id=m.dataset_id,
                field_names=json.loads(m.field_names_json or "[]"),
                rule_type=m.rule_type,
                params=json.loads(m.params_json or "{}"),
                weight=m.weight,
                is_active=m.is_active,
                change_note=m.change_note,
                changed_at=m.changed_at,
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


def _quality_score_config_to_entity(m: QualityScoreConfigModel) -> QualityScoreConfig:
    return QualityScoreConfig(
        id=m.id,
        dataset_id=m.dataset_id,
        pass_threshold=m.pass_threshold,
        rule_type_weights=json.loads(m.rule_type_weights_json or "{}"),
        version=m.version,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyQualityScoreConfigRepository(QualityScoreConfigRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, config: QualityScoreConfig) -> QualityScoreConfig:
        model = QualityScoreConfigModel(
            dataset_id=config.dataset_id,
            pass_threshold=config.pass_threshold,
            rule_type_weights_json=json.dumps(config.rule_type_weights),
            version=config.version,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        config.id = model.id
        return config

    def update(self, config: QualityScoreConfig) -> QualityScoreConfig:
        model = self._db.get(QualityScoreConfigModel, config.id)
        if model is None:
            return config
        model.dataset_id = config.dataset_id
        model.pass_threshold = config.pass_threshold
        model.rule_type_weights_json = json.dumps(config.rule_type_weights)
        model.version = config.version
        model.updated_at = config.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return config

    def get_by_id(self, config_id: int) -> Optional[QualityScoreConfig]:
        model = self._db.get(QualityScoreConfigModel, config_id)
        return _quality_score_config_to_entity(model) if model else None

    def get_by_dataset(self, dataset_id: Optional[int]) -> Optional[QualityScoreConfig]:
        stmt = select(QualityScoreConfigModel).where(
            QualityScoreConfigModel.dataset_id == dataset_id
        )
        model = self._db.execute(stmt).scalars().first()
        return _quality_score_config_to_entity(model) if model else None

    def list(self) -> List[QualityScoreConfig]:
        stmt = select(QualityScoreConfigModel).order_by(QualityScoreConfigModel.id.asc())
        return [
            _quality_score_config_to_entity(m) for m in self._db.execute(stmt).scalars().all()
        ]


class SqlAlchemyQualityScoreConfigVersionRepository(QualityScoreConfigVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: QualityScoreConfigVersion) -> QualityScoreConfigVersion:
        model = QualityScoreConfigVersionModel(
            config_id=version.config_id,
            version=version.version,
            dataset_id=version.dataset_id,
            pass_threshold=version.pass_threshold,
            rule_type_weights_json=json.dumps(version.rule_type_weights),
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_config(self, config_id: int) -> List[QualityScoreConfigVersion]:
        stmt = (
            select(QualityScoreConfigVersionModel)
            .where(QualityScoreConfigVersionModel.config_id == config_id)
            .order_by(QualityScoreConfigVersionModel.version.asc())
        )
        return [
            QualityScoreConfigVersion(
                id=m.id,
                config_id=m.config_id,
                version=m.version,
                dataset_id=m.dataset_id,
                pass_threshold=m.pass_threshold,
                rule_type_weights=json.loads(m.rule_type_weights_json or "{}"),
                change_note=m.change_note,
                changed_at=m.changed_at,
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


# ---------- UC-039: Chạy kiểm tra chất lượng dữ liệu ----------


def _quality_check_job_to_entity(m: QualityCheckJobModel) -> QualityCheckJob:
    return QualityCheckJob(
        id=m.id,
        mapping_job_id=m.mapping_job_id,
        dataset_id=m.dataset_id,
        status=m.status,
        pass_threshold=m.pass_threshold,
        records_checked=m.records_checked,
        overall_score=m.overall_score,
        rule_type_scores=json.loads(m.rule_type_scores_json or "{}"),
        published_count=m.published_count,
        exception_count=m.exception_count,
        publish_event_published=m.publish_event_published,
        exception_event_published=m.exception_event_published,
        log_entries=json.loads(m.log_entries_json or "[]"),
        error_message=m.error_message,
        received_at=m.received_at,
        completed_at=m.completed_at,
    )


class SqlAlchemyQualityCheckJobRepository(QualityCheckJobRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, job: QualityCheckJob) -> QualityCheckJob:
        model = QualityCheckJobModel(
            mapping_job_id=job.mapping_job_id,
            dataset_id=job.dataset_id,
            status=job.status,
            pass_threshold=job.pass_threshold,
            records_checked=job.records_checked,
            overall_score=job.overall_score,
            rule_type_scores_json=json.dumps(job.rule_type_scores),
            published_count=job.published_count,
            exception_count=job.exception_count,
            publish_event_published=job.publish_event_published,
            exception_event_published=job.exception_event_published,
            log_entries_json=json.dumps(job.log_entries),
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        job.id = model.id
        return job

    def update(self, job: QualityCheckJob) -> QualityCheckJob:
        model = self._db.get(QualityCheckJobModel, job.id)
        if model is None:
            return job
        model.dataset_id = job.dataset_id
        model.status = job.status
        model.pass_threshold = job.pass_threshold
        model.records_checked = job.records_checked
        model.overall_score = job.overall_score
        model.rule_type_scores_json = json.dumps(job.rule_type_scores)
        model.published_count = job.published_count
        model.exception_count = job.exception_count
        model.publish_event_published = job.publish_event_published
        model.exception_event_published = job.exception_event_published
        model.log_entries_json = json.dumps(job.log_entries)
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return job

    def get_by_id(self, quality_check_job_id: int) -> Optional[QualityCheckJob]:
        model = self._db.get(QualityCheckJobModel, quality_check_job_id)
        return _quality_check_job_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        mapping_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[QualityCheckJob]:
        stmt = select(QualityCheckJobModel)
        if dataset_id is not None:
            stmt = stmt.where(QualityCheckJobModel.dataset_id == dataset_id)
        if mapping_job_id is not None:
            stmt = stmt.where(QualityCheckJobModel.mapping_job_id == mapping_job_id)
        if status is not None:
            stmt = stmt.where(QualityCheckJobModel.status == status)
        stmt = stmt.order_by(QualityCheckJobModel.id.desc())
        return [
            _quality_check_job_to_entity(m) for m in self._db.execute(stmt).scalars().all()
        ]


class SqlAlchemyQualityCheckRuleResultRepository(QualityCheckRuleResultRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(
        self, results: List[QualityCheckRuleResult]
    ) -> List[QualityCheckRuleResult]:
        models = [
            QualityCheckRuleResultModel(
                quality_check_job_id=r.quality_check_job_id,
                rule_id=r.rule_id,
                rule_type=r.rule_type,
                field_names_json=json.dumps(r.field_names),
                total_checked=r.total_checked,
                failed_count=r.failed_count,
                pass_rate=r.pass_rate,
            )
            for r in results
        ]
        self._db.add_all(models)
        self._db.commit()
        for r, model in zip(results, models):
            self._db.refresh(model)
            r.id = model.id
        return results

    def list_for_job(self, quality_check_job_id: int) -> List[QualityCheckRuleResult]:
        stmt = (
            select(QualityCheckRuleResultModel)
            .where(QualityCheckRuleResultModel.quality_check_job_id == quality_check_job_id)
            .order_by(QualityCheckRuleResultModel.id.asc())
        )
        return [
            QualityCheckRuleResult(
                id=m.id,
                quality_check_job_id=m.quality_check_job_id,
                rule_id=m.rule_id,
                rule_type=m.rule_type,
                field_names=json.loads(m.field_names_json or "[]"),
                total_checked=m.total_checked,
                failed_count=m.failed_count,
                pass_rate=m.pass_rate,
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


class SqlAlchemyQualityPublishedRecordRepository(QualityPublishedRecordRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(
        self, records: List[QualityPublishedRecord]
    ) -> List[QualityPublishedRecord]:
        models = [
            QualityPublishedRecordModel(
                quality_check_job_id=r.quality_check_job_id,
                dataset_id=r.dataset_id,
                row_index=r.row_index,
                standardized_fields_json=json.dumps(r.standardized_fields),
            )
            for r in records
        ]
        self._db.add_all(models)
        self._db.commit()
        for r, model in zip(records, models):
            self._db.refresh(model)
            r.id = model.id
        return records

    def list_for_job(self, quality_check_job_id: int) -> List[QualityPublishedRecord]:
        stmt = (
            select(QualityPublishedRecordModel)
            .where(QualityPublishedRecordModel.quality_check_job_id == quality_check_job_id)
            .order_by(QualityPublishedRecordModel.row_index.asc())
        )
        return [
            QualityPublishedRecord(
                id=m.id,
                quality_check_job_id=m.quality_check_job_id,
                dataset_id=m.dataset_id,
                row_index=m.row_index,
                standardized_fields=json.loads(m.standardized_fields_json or "{}"),
            )
            for m in self._db.execute(stmt).scalars().all()
        ]


class SqlAlchemyQualityExceptionQueueRepository(QualityExceptionQueueRepository):
    def __init__(self, db: Session):
        self._db = db

    def add_many(
        self, items: List[QualityExceptionQueueItem]
    ) -> List[QualityExceptionQueueItem]:
        models = [
            QualityExceptionQueueItemModel(
                quality_check_job_id=i.quality_check_job_id,
                dataset_id=i.dataset_id,
                row_index=i.row_index,
                standardized_fields_json=json.dumps(i.standardized_fields),
                failed_rules_json=json.dumps(i.failed_rules),
                status=i.status,
                resolution_action=i.resolution_action,
                corrected_fields_json=(
                    json.dumps(i.corrected_fields, ensure_ascii=False) if i.corrected_fields else None
                ),
                resolution_reason=i.resolution_reason,
                resolved_at=i.resolved_at,
                created_at=i.created_at,
            )
            for i in items
        ]
        self._db.add_all(models)
        self._db.commit()
        for i, model in zip(items, models):
            self._db.refresh(model)
            i.id = model.id
        return items

    def list_for_job(self, quality_check_job_id: int) -> List[QualityExceptionQueueItem]:
        stmt = (
            select(QualityExceptionQueueItemModel)
            .where(
                QualityExceptionQueueItemModel.quality_check_job_id == quality_check_job_id
            )
            .order_by(QualityExceptionQueueItemModel.row_index.asc())
        )
        return [self._to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def list_queue(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[QualityExceptionQueueItem]:
        stmt = select(QualityExceptionQueueItemModel)
        if dataset_id is not None:
            stmt = stmt.where(QualityExceptionQueueItemModel.dataset_id == dataset_id)
        if status is not None:
            stmt = stmt.where(QualityExceptionQueueItemModel.status == status)
        stmt = stmt.order_by(QualityExceptionQueueItemModel.id.asc())
        return [self._to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def get_by_id(self, item_id: int) -> Optional[QualityExceptionQueueItem]:
        model = self._db.get(QualityExceptionQueueItemModel, item_id)
        return self._to_entity(model) if model else None

    def update(self, item: QualityExceptionQueueItem) -> QualityExceptionQueueItem:
        model = self._db.get(QualityExceptionQueueItemModel, item.id)
        if model is None:
            return item
        model.standardized_fields_json = json.dumps(item.standardized_fields, ensure_ascii=False, default=str)
        model.status = item.status
        model.resolution_action = item.resolution_action
        model.corrected_fields_json = (
            json.dumps(item.corrected_fields, ensure_ascii=False) if item.corrected_fields else None
        )
        model.resolution_reason = item.resolution_reason
        model.resolved_at = item.resolved_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return item

    @staticmethod
    def _to_entity(m: QualityExceptionQueueItemModel) -> QualityExceptionQueueItem:
        return QualityExceptionQueueItem(
            id=m.id,
            quality_check_job_id=m.quality_check_job_id,
            dataset_id=m.dataset_id,
            row_index=m.row_index,
            standardized_fields=json.loads(m.standardized_fields_json or "{}"),
            failed_rules=json.loads(m.failed_rules_json or "[]"),
            status=m.status,
            resolution_action=m.resolution_action,
            corrected_fields=json.loads(m.corrected_fields_json) if m.corrected_fields_json else {},
            resolution_reason=m.resolution_reason,
            resolved_at=m.resolved_at,
            created_at=m.created_at,
        )

# ---------- UC-041: Công bố vào kho chuẩn hoá + batch_summary ----------


def _curated_publish_job_to_entity(m: CuratedPublishJobModel) -> CuratedPublishJob:
    return CuratedPublishJob(
        id=m.id,
        quality_check_job_id=m.quality_check_job_id,
        dataset_id=m.dataset_id,
        mapping_job_id=m.mapping_job_id,
        source=m.source,
        status=m.status,
        records_received=m.records_received,
        inserted_count=m.inserted_count,
        updated_count=m.updated_count,
        batch_summary_id=m.batch_summary_id,
        published_event_published=m.published_event_published,
        log_entries=json.loads(m.log_entries_json or "[]"),
        error_message=m.error_message,
        received_at=m.received_at,
        completed_at=m.completed_at,
    )


class SqlAlchemyCuratedPublishJobRepository(CuratedPublishJobRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, job: CuratedPublishJob) -> CuratedPublishJob:
        model = CuratedPublishJobModel(
            quality_check_job_id=job.quality_check_job_id,
            dataset_id=job.dataset_id,
            mapping_job_id=job.mapping_job_id,
            source=job.source,
            status=job.status,
            records_received=job.records_received,
            inserted_count=job.inserted_count,
            updated_count=job.updated_count,
            batch_summary_id=job.batch_summary_id,
            published_event_published=job.published_event_published,
            log_entries_json=json.dumps(job.log_entries),
            error_message=job.error_message,
            received_at=job.received_at,
            completed_at=job.completed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        job.id = model.id
        return job

    def update(self, job: CuratedPublishJob) -> CuratedPublishJob:
        model = self._db.get(CuratedPublishJobModel, job.id)
        if model is None:
            return job
        model.dataset_id = job.dataset_id
        model.mapping_job_id = job.mapping_job_id
        model.source = job.source
        model.status = job.status
        model.records_received = job.records_received
        model.inserted_count = job.inserted_count
        model.updated_count = job.updated_count
        model.batch_summary_id = job.batch_summary_id
        model.published_event_published = job.published_event_published
        model.log_entries_json = json.dumps(job.log_entries)
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return job

    def get_by_id(self, curated_publish_job_id: int) -> Optional[CuratedPublishJob]:
        model = self._db.get(CuratedPublishJobModel, curated_publish_job_id)
        return _curated_publish_job_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[CuratedPublishJob]:
        stmt = select(CuratedPublishJobModel)
        if dataset_id is not None:
            stmt = stmt.where(CuratedPublishJobModel.dataset_id == dataset_id)
        if quality_check_job_id is not None:
            stmt = stmt.where(CuratedPublishJobModel.quality_check_job_id == quality_check_job_id)
        if status is not None:
            stmt = stmt.where(CuratedPublishJobModel.status == status)
        stmt = stmt.order_by(CuratedPublishJobModel.id.desc())
        return [
            _curated_publish_job_to_entity(m) for m in self._db.execute(stmt).scalars().all()
        ]


def _dm_record_to_entity(m: CuratedDmRecordModel) -> CuratedDmRecord:
    return CuratedDmRecord(
        id=m.id,
        dataset_id=m.dataset_id,
        row_index=m.row_index,
        standardized_fields=json.loads(m.standardized_fields_json or "{}"),
        publish_status=m.publish_status,
        version=m.version,
        curated_publish_job_id=m.curated_publish_job_id,
        quality_check_job_id=m.quality_check_job_id,
        source=m.source,
        first_published_at=m.first_published_at,
        last_published_at=m.last_published_at,
    )


class SqlAlchemyCuratedDmRecordRepository(CuratedDmRecordRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_dataset_and_row(
        self, dataset_id: Optional[int], row_index: int
    ) -> Optional[CuratedDmRecord]:
        stmt = select(CuratedDmRecordModel).where(
            CuratedDmRecordModel.dataset_id == dataset_id,
            CuratedDmRecordModel.row_index == row_index,
        )
        model = self._db.execute(stmt).scalars().first()
        return _dm_record_to_entity(model) if model else None

    def get_by_id(self, curated_dm_record_id: int) -> Optional[CuratedDmRecord]:
        model = self._db.get(CuratedDmRecordModel, curated_dm_record_id)
        return _dm_record_to_entity(model) if model else None

    def add(self, record: CuratedDmRecord) -> CuratedDmRecord:
        model = CuratedDmRecordModel(
            dataset_id=record.dataset_id,
            row_index=record.row_index,
            standardized_fields_json=json.dumps(record.standardized_fields, ensure_ascii=False, default=str),
            publish_status=record.publish_status,
            version=record.version,
            curated_publish_job_id=record.curated_publish_job_id,
            quality_check_job_id=record.quality_check_job_id,
            source=record.source,
            first_published_at=record.first_published_at,
            last_published_at=record.last_published_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        record.id = model.id
        return record

    def update(self, record: CuratedDmRecord) -> CuratedDmRecord:
        model = self._db.get(CuratedDmRecordModel, record.id)
        if model is None:
            return record
        model.standardized_fields_json = json.dumps(
            record.standardized_fields, ensure_ascii=False, default=str
        )
        model.publish_status = record.publish_status
        model.version = record.version
        model.curated_publish_job_id = record.curated_publish_job_id
        model.quality_check_job_id = record.quality_check_job_id
        model.source = record.source
        model.last_published_at = record.last_published_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return record

    def list_by_dataset(
        self,
        dataset_id: Optional[int] = None,
        publish_status: Optional[str] = None,
    ) -> List[CuratedDmRecord]:
        stmt = select(CuratedDmRecordModel)
        if dataset_id is not None:
            stmt = stmt.where(CuratedDmRecordModel.dataset_id == dataset_id)
        if publish_status is not None:
            stmt = stmt.where(CuratedDmRecordModel.publish_status == publish_status)
        stmt = stmt.order_by(CuratedDmRecordModel.row_index.asc())
        return [_dm_record_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

    def list_by_publish_job(self, curated_publish_job_id: int) -> List[CuratedDmRecord]:
        stmt = (
            select(CuratedDmRecordModel)
            .where(CuratedDmRecordModel.curated_publish_job_id == curated_publish_job_id)
            .order_by(CuratedDmRecordModel.row_index.asc())
        )
        return [_dm_record_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


def _batch_summary_to_entity(m: CuratedBatchSummaryModel) -> CuratedBatchSummary:
    return CuratedBatchSummary(
        id=m.id,
        curated_publish_job_id=m.curated_publish_job_id,
        dataset_id=m.dataset_id,
        quality_check_job_id=m.quality_check_job_id,
        mapping_job_id=m.mapping_job_id,
        source=m.source,
        records_received=m.records_received,
        inserted_count=m.inserted_count,
        updated_count=m.updated_count,
        created_at=m.created_at,
    )


class SqlAlchemyCuratedBatchSummaryRepository(CuratedBatchSummaryRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, summary: CuratedBatchSummary) -> CuratedBatchSummary:
        model = CuratedBatchSummaryModel(
            curated_publish_job_id=summary.curated_publish_job_id,
            dataset_id=summary.dataset_id,
            quality_check_job_id=summary.quality_check_job_id,
            mapping_job_id=summary.mapping_job_id,
            source=summary.source,
            records_received=summary.records_received,
            inserted_count=summary.inserted_count,
            updated_count=summary.updated_count,
            created_at=summary.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        summary.id = model.id
        return summary

    def get_by_id(self, batch_summary_id: int) -> Optional[CuratedBatchSummary]:
        model = self._db.get(CuratedBatchSummaryModel, batch_summary_id)
        return _batch_summary_to_entity(model) if model else None

    def list(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
    ) -> List[CuratedBatchSummary]:
        stmt = select(CuratedBatchSummaryModel)
        if dataset_id is not None:
            stmt = stmt.where(CuratedBatchSummaryModel.dataset_id == dataset_id)
        if quality_check_job_id is not None:
            stmt = stmt.where(
                CuratedBatchSummaryModel.quality_check_job_id == quality_check_job_id
            )
        stmt = stmt.order_by(CuratedBatchSummaryModel.id.desc())
        return [_batch_summary_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


def _freshness_to_entity(m: CuratedDatasetFreshnessModel) -> CuratedDatasetFreshness:
    return CuratedDatasetFreshness(
        id=m.id,
        dataset_id=m.dataset_id,
        last_batch_summary_id=m.last_batch_summary_id,
        last_published_at=m.last_published_at,
        total_published_records=m.total_published_records,
        updated_at=m.updated_at,
    )


class SqlAlchemyCuratedDatasetFreshnessRepository(CuratedDatasetFreshnessRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_dataset(self, dataset_id: Optional[int]) -> Optional[CuratedDatasetFreshness]:
        stmt = select(CuratedDatasetFreshnessModel).where(
            CuratedDatasetFreshnessModel.dataset_id == dataset_id
        )
        model = self._db.execute(stmt).scalars().first()
        return _freshness_to_entity(model) if model else None

    def upsert(self, freshness: CuratedDatasetFreshness) -> CuratedDatasetFreshness:
        model = self._db.get(CuratedDatasetFreshnessModel, freshness.id) if freshness.id else None
        if model is None:
            model = CuratedDatasetFreshnessModel(
                dataset_id=freshness.dataset_id,
                last_batch_summary_id=freshness.last_batch_summary_id,
                last_published_at=freshness.last_published_at,
                total_published_records=freshness.total_published_records,
                updated_at=freshness.updated_at,
            )
            self._db.add(model)
            self._db.commit()
            self._db.refresh(model)
            freshness.id = model.id
            return freshness
        model.last_batch_summary_id = freshness.last_batch_summary_id
        model.last_published_at = freshness.last_published_at
        model.total_published_records = freshness.total_published_records
        model.updated_at = freshness.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return freshness

    def list_all(self) -> List[CuratedDatasetFreshness]:
        stmt = select(CuratedDatasetFreshnessModel).order_by(
            CuratedDatasetFreshnessModel.dataset_id.asc()
        )
        return [_freshness_to_entity(m) for m in self._db.execute(stmt).scalars().all()]

# ---------- UC-042: Đăng ký siêu dữ liệu tập dữ liệu ----------


class SqlAlchemyDatasetMetadataRepository(DatasetMetadataRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, metadata: DatasetMetadataEntry) -> DatasetMetadataEntry:
        model = DatasetMetadataModel(
            dataset_id=metadata.dataset_id,
            owner=metadata.owner,
            description=metadata.description,
            sensitivity_level=metadata.sensitivity_level,
            version=metadata.version,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        metadata.id = model.id
        return metadata

    def update(self, metadata: DatasetMetadataEntry) -> DatasetMetadataEntry:
        model = self._db.get(DatasetMetadataModel, metadata.id)
        if model is None:
            return metadata
        model.owner = metadata.owner
        model.description = metadata.description
        model.sensitivity_level = metadata.sensitivity_level
        model.version = metadata.version
        model.updated_at = metadata.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return metadata

    def get_by_id(self, metadata_id: int) -> Optional[DatasetMetadataEntry]:
        model = self._db.get(DatasetMetadataModel, metadata_id)
        return _dataset_metadata_to_entity(model) if model else None

    def get_by_dataset_id(self, dataset_id: int) -> Optional[DatasetMetadataEntry]:
        stmt = select(DatasetMetadataModel).where(DatasetMetadataModel.dataset_id == dataset_id)
        model = self._db.execute(stmt).scalars().first()
        return _dataset_metadata_to_entity(model) if model else None

    def list(
        self,
        sensitivity_level: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[DatasetMetadataEntry]:
        stmt = select(DatasetMetadataModel)
        if sensitivity_level:
            stmt = stmt.where(DatasetMetadataModel.sensitivity_level == sensitivity_level)
        if owner:
            stmt = stmt.where(DatasetMetadataModel.owner == owner)
        stmt = stmt.order_by(DatasetMetadataModel.dataset_id.asc())
        return [_dataset_metadata_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyDatasetMetadataVersionRepository(DatasetMetadataVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: DatasetMetadataVersion) -> DatasetMetadataVersion:
        model = DatasetMetadataVersionModel(
            dataset_metadata_id=version.dataset_metadata_id,
            dataset_id=version.dataset_id,
            version=version.version,
            owner=version.owner,
            description=version.description,
            sensitivity_level=version.sensitivity_level,
            change_note=version.change_note,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_metadata(self, dataset_metadata_id: int) -> List[DatasetMetadataVersion]:
        stmt = (
            select(DatasetMetadataVersionModel)
            .where(DatasetMetadataVersionModel.dataset_metadata_id == dataset_metadata_id)
            .order_by(DatasetMetadataVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                DatasetMetadataVersion(
                    id=m.id,
                    dataset_metadata_id=m.dataset_metadata_id,
                    dataset_id=m.dataset_id,
                    version=m.version,
                    owner=m.owner,
                    description=m.description,
                    sensitivity_level=m.sensitivity_level,
                    change_note=m.change_note,
                    changed_at=m.changed_at,
                )
            )
        return result


def _dataset_metadata_to_entity(m: DatasetMetadataModel) -> DatasetMetadataEntry:
    return DatasetMetadataEntry(
        id=m.id,
        dataset_id=m.dataset_id,
        owner=m.owner,
        description=m.description,
        sensitivity_level=m.sensitivity_level,
        version=m.version,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )

# ---------- UC-043: Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa ----------


class SqlAlchemySemanticIndicatorRepository(SemanticIndicatorRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, indicator: SemanticIndicator) -> SemanticIndicator:
        model = SemanticIndicatorModel(
            name=indicator.name,
            description=indicator.description,
            expression=indicator.expression,
            domain=indicator.domain,
            status=indicator.status,
            version=indicator.version,
            created_by=indicator.created_by,
            created_at=indicator.created_at,
            updated_at=indicator.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        indicator.id = model.id
        return indicator

    def update(self, indicator: SemanticIndicator) -> SemanticIndicator:
        model = self._db.get(SemanticIndicatorModel, indicator.id)
        if model is None:
            return indicator
        model.name = indicator.name
        model.description = indicator.description
        model.expression = indicator.expression
        model.domain = indicator.domain
        model.status = indicator.status
        model.version = indicator.version
        model.updated_at = indicator.updated_at
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return indicator

    def get_by_id(self, indicator_id: int) -> Optional[SemanticIndicator]:
        model = self._db.get(SemanticIndicatorModel, indicator_id)
        return _semantic_indicator_to_entity(model) if model else None

    def get_by_name(self, name: str) -> Optional[SemanticIndicator]:
        stmt = select(SemanticIndicatorModel).where(SemanticIndicatorModel.name == name)
        model = self._db.execute(stmt).scalars().first()
        return _semantic_indicator_to_entity(model) if model else None

    def list(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SemanticIndicator]:
        stmt = select(SemanticIndicatorModel)
        if domain:
            stmt = stmt.where(SemanticIndicatorModel.domain == domain)
        if status:
            stmt = stmt.where(SemanticIndicatorModel.status == status)
        stmt = stmt.order_by(SemanticIndicatorModel.id.desc())
        return [_semantic_indicator_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemySemanticIndicatorVersionRepository(SemanticIndicatorVersionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, version: SemanticIndicatorVersion) -> SemanticIndicatorVersion:
        model = SemanticIndicatorVersionModel(
            indicator_id=version.indicator_id,
            version=version.version,
            name=version.name,
            description=version.description,
            expression=version.expression,
            domain=version.domain,
            status=version.status,
            change_note=version.change_note,
            changed_by=version.changed_by,
            changed_at=version.changed_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        version.id = model.id
        return version

    def list_for_indicator(self, indicator_id: int) -> List[SemanticIndicatorVersion]:
        stmt = (
            select(SemanticIndicatorVersionModel)
            .where(SemanticIndicatorVersionModel.indicator_id == indicator_id)
            .order_by(SemanticIndicatorVersionModel.version.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                SemanticIndicatorVersion(
                    id=m.id,
                    indicator_id=m.indicator_id,
                    version=m.version,
                    name=m.name,
                    description=m.description,
                    expression=m.expression,
                    domain=m.domain,
                    status=m.status,
                    change_note=m.change_note,
                    changed_by=m.changed_by,
                    changed_at=m.changed_at,
                )
            )
        return result


class SqlAlchemyIndicatorTestRunRepository(IndicatorTestRunRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, test_run: IndicatorTestRun) -> IndicatorTestRun:
        model = IndicatorTestRunModel(
            indicator_id=test_run.indicator_id,
            expression_snapshot=test_run.expression_snapshot,
            sample_rows_json=json.dumps(test_run.sample_rows),
            status=test_run.status,
            result_value=test_run.result_value,
            error_message=test_run.error_message,
            tested_by=test_run.tested_by,
            tested_at=test_run.tested_at,
            indicator_status_snapshot=test_run.indicator_status_snapshot,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        test_run.id = model.id
        return test_run

    def get_by_id(self, test_run_id: int) -> Optional[IndicatorTestRun]:
        model = self._db.get(IndicatorTestRunModel, test_run_id)
        return _indicator_test_run_to_entity(model) if model else None

    def list_for_indicator(self, indicator_id: int) -> List[IndicatorTestRun]:
        stmt = (
            select(IndicatorTestRunModel)
            .where(IndicatorTestRunModel.indicator_id == indicator_id)
            .order_by(IndicatorTestRunModel.id.desc())
        )
        return [_indicator_test_run_to_entity(m) for m in self._db.execute(stmt).scalars().all()]


class SqlAlchemyIndicatorAuditLogRepository(IndicatorAuditLogRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, log: IndicatorAuditLog) -> IndicatorAuditLog:
        model = IndicatorAuditLogModel(
            indicator_id=log.indicator_id,
            action=log.action,
            actor=log.actor,
            detail_json=json.dumps(log.detail or {}),
            created_at=log.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        log.id = model.id
        return log

    def list_for_indicator(self, indicator_id: int) -> List[IndicatorAuditLog]:
        stmt = (
            select(IndicatorAuditLogModel)
            .where(IndicatorAuditLogModel.indicator_id == indicator_id)
            .order_by(IndicatorAuditLogModel.id.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                IndicatorAuditLog(
                    id=m.id,
                    indicator_id=m.indicator_id,
                    action=m.action,
                    actor=m.actor,
                    detail=json.loads(m.detail_json or "{}"),
                    created_at=m.created_at,
                )
            )
        return result


def _semantic_indicator_to_entity(m: SemanticIndicatorModel) -> SemanticIndicator:
    return SemanticIndicator(
        id=m.id,
        name=m.name,
        description=m.description,
        expression=m.expression,
        domain=m.domain,
        status=m.status,
        version=m.version,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _indicator_test_run_to_entity(m: IndicatorTestRunModel) -> IndicatorTestRun:
    return IndicatorTestRun(
        id=m.id,
        indicator_id=m.indicator_id,
        expression_snapshot=m.expression_snapshot,
        sample_rows=json.loads(m.sample_rows_json or "[]"),
        status=m.status,
        result_value=m.result_value,
        error_message=m.error_message,
        tested_by=m.tested_by,
        tested_at=m.tested_at,
        indicator_status_snapshot=m.indicator_status_snapshot,
    )


# ---------- UC-044: Phê duyệt chỉ tiêu ----------


class SqlAlchemyIndicatorApprovalDecisionRepository(IndicatorApprovalDecisionRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, decision: IndicatorApprovalDecision) -> IndicatorApprovalDecision:
        model = IndicatorApprovalDecisionModel(
            indicator_id=decision.indicator_id,
            action=decision.action,
            decided_by=decision.decided_by,
            decision_reason=decision.decision_reason,
            comparison_snapshot_json=json.dumps(decision.comparison_snapshot or {}),
            created_at=decision.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        decision.id = model.id
        return decision

    def list_for_indicator(self, indicator_id: int) -> List[IndicatorApprovalDecision]:
        stmt = (
            select(IndicatorApprovalDecisionModel)
            .where(IndicatorApprovalDecisionModel.indicator_id == indicator_id)
            .order_by(IndicatorApprovalDecisionModel.id.desc())
        )
        result = []
        for m in self._db.execute(stmt).scalars().all():
            result.append(
                IndicatorApprovalDecision(
                    id=m.id,
                    indicator_id=m.indicator_id,
                    action=m.action,
                    decided_by=m.decided_by,
                    decision_reason=m.decision_reason,
                    comparison_snapshot=json.loads(m.comparison_snapshot_json or "{}"),
                    created_at=m.created_at,
                )
            )
        return result