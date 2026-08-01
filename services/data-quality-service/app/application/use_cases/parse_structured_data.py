"""Application layer — UC-029: Phân tích dữ liệu có cấu trúc.

Đối chiếu docs/use_cases.json id=29: actor "Hệ thống tự động (Bộ phân
tích cú pháp)". Luồng nghiệp vụ:
1. Nhận sự kiện `parsing.requested` (tạo `ParsingJob` mới, status=RECEIVED).
2. Hệ thống đọc dữ liệu thô (từ MinIO qua `FileStorage`, theo
   `raw_object_key`) -> lưu bản sao từng dòng vào bảng `stg_*`
   (`stg_structured_rows`).
3. Phân tích Excel/CSV/JSON/XML theo lược đồ (`schema_fields`).
4. Hệ thống ánh xạ tên trường + ép kiểu -> lưu vào
   `parsed_structured_records` + `parsing_row_errors` (lỗi từng dòng/trường,
   không làm hỏng cả job).
5-6. Kích hoạt + đẩy sự kiện `mapping.requested` (chỉ khi có ít nhất 1 bản
   ghi phân tích thành công) cho UC-031 (Ánh xạ trường sang dạng chuẩn).

Toàn bộ 6 bước chạy tự động, liền mạch trong 1 lần gọi `receive_and_process()`
(actor là hệ thống tự động, không có bước thao tác thủ công xen giữa) —
cùng tinh thần với UC-025 `IncrementalSyncService.run_sync()` bên
ingestion-service: 1 lần gọi = trọn vòng đời 1 `ParsingJob`, có log từng
bước + tổng kiểm soát, để tiện xem lại/gỡ lỗi qua API.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import ParsedRecord, ParsingJob, ParsingRowError
from app.domain.exceptions import (
    InvalidParsingJob,
    ParsingJobNotFound,
    RawObjectNotFound,
    UnsupportedSourceFormat,
)
from app.domain.repositories import (
    EventPublisher,
    FileStorage,
    ParsedRecordRepository,
    ParsingJobRepository,
    ParsingRowErrorRepository,
    StgStructuredRowRepository,
)
from app.infrastructure.structured_parser import (
    ParseError,
    build_auto_field_mapping,
    map_and_cast_row,
    parse_raw_bytes,
)

MAPPING_REQUESTED_EVENT = "mapping.requested"

SOURCE_FORMAT_BY_EXTENSION = {
    ".csv": "CSV",
    ".json": "JSON",
    ".xml": "XML",
    ".xlsx": "EXCEL",
    ".xls": "EXCEL",
}


def infer_source_format(raw_object_key: str) -> Optional[str]:
    lowered = raw_object_key.lower()
    for ext, fmt in SOURCE_FORMAT_BY_EXTENSION.items():
        if lowered.endswith(ext):
            return fmt
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StructuredParsingService:
    def __init__(
        self,
        job_repo: ParsingJobRepository,
        stg_row_repo: StgStructuredRowRepository,
        parsed_record_repo: ParsedRecordRepository,
        row_error_repo: ParsingRowErrorRepository,
        file_storage: FileStorage,
        event_publisher: EventPublisher,
    ):
        self._jobs = job_repo
        self._stg_rows = stg_row_repo
        self._parsed_records = parsed_record_repo
        self._row_errors = row_error_repo
        self._storage = file_storage
        self._events = event_publisher

    # ---------- Bước 1: nhận sự kiện parsing.requested + chạy trọn vòng đời ----------

    def receive_and_process(
        self,
        dataset_id: int,
        raw_object_key: str,
        schema_fields: List[Dict[str, Any]],
        source_format: Optional[str] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        ingestion_run_id: Optional[int] = None,
        data_source_id: Optional[int] = None,
    ) -> ParsingJob:
        resolved_format = source_format or infer_source_format(raw_object_key)
        if not resolved_format:
            raise UnsupportedSourceFormat(str(source_format))

        try:
            job = ParsingJob(
                id=None,
                dataset_id=dataset_id,
                source_format=resolved_format,
                raw_object_key=raw_object_key,
                schema_fields=schema_fields,
                field_mapping=field_mapping or {},
                ingestion_run_id=ingestion_run_id,
                data_source_id=data_source_id,
                status="RECEIVED",
            )
        except ValueError as exc:
            raise InvalidParsingJob(str(exc)) from exc

        job.append_log(
            "INFO",
            f"Nhận sự kiện parsing.requested: dataset_id={dataset_id}, "
            f"raw_object_key='{raw_object_key}', source_format={resolved_format}",
        )
        job = self._jobs.add(job)
        job = self._jobs.update(job)

        return self._run_pipeline(job)

    # ---------- Bước 2-6: chạy pipeline cho 1 job đã nhận ----------

    def _run_pipeline(self, job: ParsingJob) -> ParsingJob:
        job.start_running()
        job = self._jobs.update(job)

        # Bước 2: đọc dữ liệu thô -> stg_*
        try:
            raw_content = self._storage.download(job.raw_object_key)
        except (FileNotFoundError, OSError) as exc:
            job.append_log("ERROR", f"Không đọc được dữ liệu thô: {exc}")
            job = self._jobs.update(job)
            job.complete(
                status="FAILED",
                records_read=0,
                records_parsed=0,
                records_failed=0,
                error_message=str(RawObjectNotFound(job.raw_object_key)),
            )
            return self._jobs.update(job)

        try:
            raw_rows = parse_raw_bytes(raw_content, job.source_format)
        except ParseError as exc:
            job.append_log("ERROR", f"Lỗi phân tích cú pháp: {exc}")
            job = self._jobs.update(job)
            job.complete(
                status="FAILED",
                records_read=0,
                records_parsed=0,
                records_failed=0,
                error_message=str(exc),
            )
            return self._jobs.update(job)

        self._stg_rows.add_many(job.id, raw_rows)
        job.append_log(
            "INFO", f"Đã đọc {len(raw_rows)} dòng dữ liệu thô, lưu vào stg_structured_rows"
        )
        job = self._jobs.update(job)

        # Bước 3-4: ánh xạ tên trường + ép kiểu theo lược đồ
        field_mapping = job.field_mapping
        if not field_mapping and raw_rows:
            field_mapping = build_auto_field_mapping(list(raw_rows[0].keys()), job.schema_fields)
            job.append_log(
                "INFO",
                f"Không có field_mapping tường minh — tự ánh xạ theo tên trùng khớp: "
                f"{field_mapping}",
            )
            job = self._jobs.update(job)

        parsed_records: List[ParsedRecord] = []
        row_errors: List[ParsingRowError] = []
        records_failed = 0
        for idx, raw_row in enumerate(raw_rows):
            mapped_fields, errors = map_and_cast_row(raw_row, job.schema_fields, field_mapping)
            has_error = bool(errors)
            if has_error:
                records_failed += 1
                for field_name, message in errors:
                    row_errors.append(
                        ParsingRowError(
                            id=None,
                            parsing_job_id=job.id,
                            row_index=idx,
                            field_name=field_name,
                            message=message,
                        )
                    )
            parsed_records.append(
                ParsedRecord(
                    id=None,
                    parsing_job_id=job.id,
                    row_index=idx,
                    mapped_fields=mapped_fields,
                    has_error=has_error,
                )
            )

        if parsed_records:
            self._parsed_records.add_many(parsed_records)
        if row_errors:
            self._row_errors.add_many(row_errors)

        records_parsed = len(parsed_records) - records_failed
        job.append_log(
            "INFO",
            f"Đã ánh xạ + ép kiểu {len(parsed_records)} dòng: thành công {records_parsed}, "
            f"lỗi {records_failed}",
        )
        job = self._jobs.update(job)

        # Bước 5-6: kích hoạt + đẩy sự kiện mapping.requested (chỉ khi có
        # ít nhất 1 bản ghi phân tích thành công).
        mapping_event_published = False
        if records_parsed > 0:
            self._events.publish(
                MAPPING_REQUESTED_EVENT,
                {
                    "parsing_job_id": job.id,
                    "dataset_id": job.dataset_id,
                    "ingestion_run_id": job.ingestion_run_id,
                    "records_parsed": records_parsed,
                    "records_failed": records_failed,
                },
            )
            mapping_event_published = True
            job.append_log("INFO", "Đã kích hoạt + đẩy sự kiện mapping.requested")
            job = self._jobs.update(job)

        final_status = "MAPPED" if records_parsed > 0 else "FAILED"
        error_message = None
        if final_status == "FAILED":
            error_message = "Không có dòng nào ánh xạ + ép kiểu thành công"
        job.complete(
            status=final_status,
            records_read=len(raw_rows),
            records_parsed=records_parsed,
            records_failed=records_failed,
            mapping_event_published=mapping_event_published,
            error_message=error_message,
        )
        return self._jobs.update(job)

    # ---------- Xem lại ----------

    def get(self, parsing_job_id: int) -> ParsingJob:
        job = self._jobs.get_by_id(parsing_job_id)
        if job is None:
            raise ParsingJobNotFound(parsing_job_id)
        return job

    def list_jobs(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
        ingestion_run_id: Optional[int] = None,
    ) -> List[ParsingJob]:
        return self._jobs.list(dataset_id=dataset_id, status=status, ingestion_run_id=ingestion_run_id)

    def list_row_errors(self, parsing_job_id: int) -> List[ParsingRowError]:
        if self._jobs.get_by_id(parsing_job_id) is None:
            raise ParsingJobNotFound(parsing_job_id)
        return self._row_errors.list_for_job(parsing_job_id)

    def list_stg_rows(self, parsing_job_id: int) -> List[Dict[str, Any]]:
        if self._jobs.get_by_id(parsing_job_id) is None:
            raise ParsingJobNotFound(parsing_job_id)
        return self._stg_rows.list_for_job(parsing_job_id)

    def list_parsed_records(self, parsing_job_id: int) -> List[ParsedRecord]:
        if self._jobs.get_by_id(parsing_job_id) is None:
            raise ParsingJobNotFound(parsing_job_id)
        return self._parsed_records.list_for_job(parsing_job_id)