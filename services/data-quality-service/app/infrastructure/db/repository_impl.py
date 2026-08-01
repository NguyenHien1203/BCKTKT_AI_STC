"""SqlAlchemy repository implementations cho data-quality-service — UC-029."""
import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    OcrExtractedTable,
    OcrJob,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
)
from app.domain.repositories import (
    OcrExtractedTableRepository,
    OcrJobRepository,
    ParsedRecordRepository,
    ParsingJobRepository,
    ParsingRowErrorRepository,
    StgStructuredRowRepository,
)
from app.infrastructure.db.models import (
    OcrExtractedTableModel,
    OcrJobModel,
    ParsedStructuredRecordModel,
    ParsingJobModel,
    ParsingRowErrorModel,
    StgStructuredRowModel,
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