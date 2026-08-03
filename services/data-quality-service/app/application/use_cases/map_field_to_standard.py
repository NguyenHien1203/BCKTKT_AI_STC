"""Application layer — UC-031: Ánh xạ trường sang dạng chuẩn.

Đối chiếu docs/use_cases.json id=31: actor "Hệ thống tự động (Bộ ánh xạ
dữ liệu)". Luồng nghiệp vụ:
1. Tra cứu quy tắc ánh xạ (có phiên bản). Hệ thống đọc
   `metadata.mapping_rules`. Áp dụng quy tắc + tra cứu danh mục chuẩn.
   Hệ thống chuẩn hóa field.
2. Từ chối trường bắt buộc bị NULL. Hệ thống ghi vào
   `metadata.mapping_rejections`.
3. Đẩy giá trị chưa ánh xạ vào hàng đợi. Hệ thống đẩy vào hàng đợi chưa
   ánh xạ cho Phụ trách Dữ liệu (UC-032 Xử lý hàng đợi chưa ánh xạ).

Toàn bộ chạy tự động, liền mạch trong 1 lần gọi `receive_and_process()`
(actor là hệ thống tự động) -- nhận sự kiện `mapping.requested` (phát bởi
UC-029/UC-030 sau khi ánh xạ tên trường + ép kiểu xong, xem
`app/application/use_cases/parse_structured_data.py`,
`MAPPING_REQUESTED_EVENT`) rồi đọc lại các `ParsedRecord` (bước 4 của
UC-029, `has_error=False`) của `parsing_job_id` tương ứng để chuẩn hoá
tiếp -- cùng tinh thần `StructuredParsingService.receive_and_process()`.

"Trường bắt buộc" (bước 2) lấy từ `ParsingJob.schema_fields` (đã có sẵn
`nullable`, denormalized từ `Dataset.schema_fields` UC-018) -- không phụ
thuộc `MappingRule`, vì 1 trường có thể bắt buộc mà không cần quy tắc
chuẩn hoá nào (vd trường kiểu số/ngày không cần tra danh mục).
"""
from typing import Dict, List, Optional

from app.domain.entities import (
    MappedStandardRecord,
    MappingJob,
    MappingRejection,
    UnmappedQueueItem,
)
from app.domain.exceptions import (
    InvalidMappingJob,
    MappingJobNotFound,
    NoParsedRecordsToMap,
    ParsingJobNotFound,
)
from app.domain.repositories import (
    MappedStandardRecordRepository,
    MappingJobRepository,
    MappingRejectionRepository,
    MappingRuleRepository,
    ParsedRecordRepository,
    ParsingJobRepository,
    UnmappedQueueRepository,
)
from app.infrastructure.field_normalizer import apply_rule, is_empty


class FieldMappingService:
    def __init__(
        self,
        mapping_job_repo: MappingJobRepository,
        mapping_rule_repo: MappingRuleRepository,
        rejection_repo: MappingRejectionRepository,
        unmapped_queue_repo: UnmappedQueueRepository,
        standard_record_repo: MappedStandardRecordRepository,
        parsed_record_repo: ParsedRecordRepository,
        parsing_job_repo: ParsingJobRepository,
    ):
        self._jobs = mapping_job_repo
        self._rules = mapping_rule_repo
        self._rejections = rejection_repo
        self._unmapped_queue = unmapped_queue_repo
        self._standard_records = standard_record_repo
        self._parsed_records = parsed_record_repo
        self._parsing_jobs = parsing_job_repo

    # ---------- Nhận sự kiện mapping.requested + chạy trọn vòng đời ----------

    def receive_and_process(
        self,
        parsing_job_id: int,
        dataset_id: Optional[int] = None,
    ) -> MappingJob:
        parsing_job = self._parsing_jobs.get_by_id(parsing_job_id)
        if parsing_job is None:
            raise ParsingJobNotFound(parsing_job_id)

        resolved_dataset_id = dataset_id or parsing_job.dataset_id

        try:
            job = MappingJob(
                id=None,
                parsing_job_id=parsing_job_id,
                dataset_id=resolved_dataset_id,
                status="RECEIVED",
            )
        except ValueError as exc:
            raise InvalidMappingJob(str(exc)) from exc

        job.append_log(
            "INFO",
            f"Nhận sự kiện mapping.requested: parsing_job_id={parsing_job_id}, "
            f"dataset_id={resolved_dataset_id}",
        )
        job = self._jobs.add(job)
        job = self._jobs.update(job)

        return self._run_pipeline(job, parsing_job.schema_fields)

    def _run_pipeline(self, job: MappingJob, schema_fields: List[Dict]) -> MappingJob:
        job.start_running()
        job = self._jobs.update(job)

        parsed_records = [
            r for r in self._parsed_records.list_for_job(job.parsing_job_id) if not r.has_error
        ]
        if not parsed_records:
            job.append_log(
                "ERROR",
                f"Không có bản ghi hợp lệ nào (has_error=False) của "
                f"parsing_job_id={job.parsing_job_id} để ánh xạ chuẩn hoá",
            )
            job = self._jobs.update(job)
            job.complete(
                status="FAILED",
                records_total=0,
                records_mapped=0,
                records_rejected=0,
                unmapped_values_count=0,
                error_message=str(NoParsedRecordsToMap(job.parsing_job_id)),
            )
            return self._jobs.update(job)

        # Bước 1: Tra cứu quy tắc ánh xạ (có phiên bản).
        rules = self._rules.get_active_rules_for_dataset(job.dataset_id)
        job.append_log(
            "INFO",
            f"Đã tra cứu {len(rules)} quy tắc ánh xạ đang áp dụng cho dataset_id={job.dataset_id}: "
            f"{sorted(rules.keys())}",
        )
        job = self._jobs.update(job)

        required_fields = {
            f["name"] for f in schema_fields if f.get("nullable") is False and f.get("name")
        }

        standard_records: List[MappedStandardRecord] = []
        rejections: List[MappingRejection] = []
        unmapped_items: List[UnmappedQueueItem] = []

        for record in parsed_records:
            standardized_fields: Dict = {}
            row_unmapped_count = 0
            for field_name, raw_value in record.mapped_fields.items():
                rule = rules.get(field_name)
                standardized_value, unmapped = apply_rule(rule, raw_value)
                standardized_fields[field_name] = standardized_value
                if unmapped:
                    row_unmapped_count += 1
                    unmapped_items.append(
                        UnmappedQueueItem(
                            id=None,
                            mapping_job_id=job.id,
                            dataset_id=job.dataset_id,
                            row_index=record.row_index,
                            field_name=field_name,
                            raw_value=str(raw_value),
                        )
                    )

            # Bước 2: Từ chối trường bắt buộc bị NULL.
            missing_required = [
                f for f in required_fields if is_empty(standardized_fields.get(f))
            ]
            if missing_required:
                for field_name in missing_required:
                    rejections.append(
                        MappingRejection(
                            id=None,
                            mapping_job_id=job.id,
                            row_index=record.row_index,
                            field_name=field_name,
                            reason=(
                                f"Trường bắt buộc '{field_name}' có giá trị rỗng (NULL) "
                                "sau khi ánh xạ chuẩn hoá"
                            ),
                        )
                    )
                continue

            standard_records.append(
                MappedStandardRecord(
                    id=None,
                    mapping_job_id=job.id,
                    row_index=record.row_index,
                    standardized_fields=standardized_fields,
                )
            )

        if standard_records:
            self._standard_records.add_many(standard_records)
        # Bước 2 kết quả: ghi vào metadata.mapping_rejections.
        if rejections:
            self._rejections.add_many(rejections)
        # Bước 3: đẩy giá trị chưa ánh xạ vào hàng đợi.
        if unmapped_items:
            self._unmapped_queue.add_many(unmapped_items)

        records_rejected = len({(r.row_index) for r in rejections})
        job.append_log(
            "INFO",
            f"Đã ánh xạ chuẩn hoá {len(parsed_records)} dòng: thành công "
            f"{len(standard_records)}, từ chối {records_rejected}, "
            f"giá trị chưa ánh xạ đẩy vào hàng đợi {len(unmapped_items)}",
        )
        job = self._jobs.update(job)

        job.complete(
            status="COMPLETED",
            records_total=len(parsed_records),
            records_mapped=len(standard_records),
            records_rejected=records_rejected,
            unmapped_values_count=len(unmapped_items),
        )
        return self._jobs.update(job)

    # ---------- Xem lại ----------

    def get(self, mapping_job_id: int) -> MappingJob:
        job = self._jobs.get_by_id(mapping_job_id)
        if job is None:
            raise MappingJobNotFound(mapping_job_id)
        return job

    def list_jobs(
        self,
        dataset_id: Optional[int] = None,
        parsing_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[MappingJob]:
        return self._jobs.list(dataset_id=dataset_id, parsing_job_id=parsing_job_id, status=status)

    def list_rejections(self, mapping_job_id: int) -> List[MappingRejection]:
        if self._jobs.get_by_id(mapping_job_id) is None:
            raise MappingJobNotFound(mapping_job_id)
        return self._rejections.list_for_job(mapping_job_id)

    def list_unmapped_queue(self, mapping_job_id: int) -> List[UnmappedQueueItem]:
        if self._jobs.get_by_id(mapping_job_id) is None:
            raise MappingJobNotFound(mapping_job_id)
        return self._unmapped_queue.list_for_job(mapping_job_id)

    def list_standard_records(self, mapping_job_id: int) -> List[MappedStandardRecord]:
        if self._jobs.get_by_id(mapping_job_id) is None:
            raise MappingJobNotFound(mapping_job_id)
        return self._standard_records.list_for_job(mapping_job_id)