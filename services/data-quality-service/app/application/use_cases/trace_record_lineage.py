"""UC-045: Truy vết nguồn gốc bản ghi (docs/use_cases.json id=45).

Actor: "Kiểm toán viên". Luồng nghiệp vụ:
1. Chọn bản ghi curated. Hệ thống hiển thị (dùng lại `GET
   /curated-publish/dm-records` của UC-041 để chọn bản ghi -- xem
   `curated_publish_router.py`).
2. Xem nguồn gốc dữ liệu qua các bước (thô -> phân tích -> ánh xạ ->
   chất lượng -> công bố). Hệ thống hiển thị chuỗi.
3. Xem chi tiết từng bước. Hệ thống hiển thị dữ liệu vào/ra + phép
   biến đổi.

Đây là use case CHỈ ĐỌC (read-only) -- không tạo bảng mới, không thay
đổi dữ liệu. Dựa hoàn toàn vào `row_index` được giữ nguyên xuyên suốt
chuỗi xử lý (ParsingJob -> MappingJob -> QualityCheckJob -> CuratedDmRecord,
mỗi bước đều lưu `row_index` của cùng 1 dòng dữ liệu nguồn) để dựng lại
5 bước:

    RAW (thô) -> PARSING (phân tích) -> MAPPING (ánh xạ)
    -> QUALITY (chất lượng) -> PUBLISH (công bố)

Xuất phát điểm là 1 `CuratedDmRecord` (bảng ``dm_records``, đầu ra
UC-041) -- lần ngược lại theo các khoá ngoại đã có sẵn:

    CuratedDmRecord.quality_check_job_id -> QualityCheckJob
    QualityCheckJob.mapping_job_id       -> MappingJob
    MappingJob.parsing_job_id            -> ParsingJob
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    CuratedDmRecord,
    MappingJob,
    ParsingJob,
    QualityCheckJob,
)
from app.domain.exceptions import CuratedDmRecordNotFound, InvalidLineageStep
from app.domain.repositories import (
    CuratedBatchSummaryRepository,
    CuratedDmRecordRepository,
    CuratedPublishJobRepository,
    MappedStandardRecordRepository,
    MappingJobRepository,
    MappingRejectionRepository,
    ParsedRecordRepository,
    ParsingJobRepository,
    ParsingRowErrorRepository,
    QualityCheckJobRepository,
    QualityCheckRuleResultRepository,
    QualityExceptionQueueRepository,
    QualityPublishedRecordRepository,
    StgStructuredRowRepository,
)

STEP_RAW = "RAW"
STEP_PARSING = "PARSING"
STEP_MAPPING = "MAPPING"
STEP_QUALITY = "QUALITY"
STEP_PUBLISH = "PUBLISH"

LINEAGE_STEPS = (STEP_RAW, STEP_PARSING, STEP_MAPPING, STEP_QUALITY, STEP_PUBLISH)

STEP_LABELS = {
    STEP_RAW: "Dữ liệu thô",
    STEP_PARSING: "Phân tích",
    STEP_MAPPING: "Ánh xạ",
    STEP_QUALITY: "Chất lượng",
    STEP_PUBLISH: "Công bố",
}


@dataclass
class LineageStepSummary:
    """Bước 2 'Xem nguồn gốc dữ liệu qua các bước': 1 mắt xích trong chuỗi."""

    step: str
    label: str
    available: bool
    job_id: Optional[int] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


@dataclass
class LineageChain:
    curated_dm_record_id: int
    dataset_id: Optional[int]
    row_index: int
    steps: List[LineageStepSummary] = field(default_factory=list)


@dataclass
class LineageStepDetail:
    """Bước 3 'Xem chi tiết từng bước': dữ liệu vào/ra + phép biến đổi."""

    step: str
    label: str
    available: bool
    input: Any = None
    output: Any = None
    transformation: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    note: Optional[str] = None


class RecordLineageService:
    def __init__(
        self,
        dm_record_repo: CuratedDmRecordRepository,
        curated_publish_job_repo: CuratedPublishJobRepository,
        batch_summary_repo: CuratedBatchSummaryRepository,
        quality_check_job_repo: QualityCheckJobRepository,
        quality_rule_result_repo: QualityCheckRuleResultRepository,
        quality_published_repo: QualityPublishedRecordRepository,
        quality_exception_repo: QualityExceptionQueueRepository,
        mapping_job_repo: MappingJobRepository,
        mapping_rejection_repo: MappingRejectionRepository,
        mapped_record_repo: MappedStandardRecordRepository,
        parsing_job_repo: ParsingJobRepository,
        stg_row_repo: StgStructuredRowRepository,
        parsed_record_repo: ParsedRecordRepository,
        parsing_row_error_repo: ParsingRowErrorRepository,
    ) -> None:
        self.dm_record_repo = dm_record_repo
        self.curated_publish_job_repo = curated_publish_job_repo
        self.batch_summary_repo = batch_summary_repo
        self.quality_check_job_repo = quality_check_job_repo
        self.quality_rule_result_repo = quality_rule_result_repo
        self.quality_published_repo = quality_published_repo
        self.quality_exception_repo = quality_exception_repo
        self.mapping_job_repo = mapping_job_repo
        self.mapping_rejection_repo = mapping_rejection_repo
        self.mapped_record_repo = mapped_record_repo
        self.parsing_job_repo = parsing_job_repo
        self.stg_row_repo = stg_row_repo
        self.parsed_record_repo = parsed_record_repo
        self.parsing_row_error_repo = parsing_row_error_repo

    # ---------- nội bộ: dựng lại ngữ cảnh chuỗi từ 1 bản ghi curated ----------

    def _load_context(self, curated_dm_record_id: int):
        dm: Optional[CuratedDmRecord] = self.dm_record_repo.get_by_id(curated_dm_record_id)
        if dm is None:
            raise CuratedDmRecordNotFound(curated_dm_record_id)

        quality_job: Optional[QualityCheckJob] = None
        if dm.quality_check_job_id:
            quality_job = self.quality_check_job_repo.get_by_id(dm.quality_check_job_id)

        mapping_job: Optional[MappingJob] = None
        if quality_job and quality_job.mapping_job_id:
            mapping_job = self.mapping_job_repo.get_by_id(quality_job.mapping_job_id)

        parsing_job: Optional[ParsingJob] = None
        if mapping_job and mapping_job.parsing_job_id:
            parsing_job = self.parsing_job_repo.get_by_id(mapping_job.parsing_job_id)

        return dm, quality_job, mapping_job, parsing_job

    # ---------- Bước 1 (dùng bởi router để chọn bản ghi) ----------

    def get_curated_record(self, curated_dm_record_id: int) -> CuratedDmRecord:
        dm = self.dm_record_repo.get_by_id(curated_dm_record_id)
        if dm is None:
            raise CuratedDmRecordNotFound(curated_dm_record_id)
        return dm

    # ---------- Bước 2: 'Xem nguồn gốc dữ liệu qua các bước' ----------

    def get_chain(self, curated_dm_record_id: int) -> LineageChain:
        dm, quality_job, mapping_job, parsing_job = self._load_context(curated_dm_record_id)
        row_index = dm.row_index

        steps: List[LineageStepSummary] = []

        # RAW + PARSING đều bắt nguồn từ ParsingJob (UC-029: đọc thô -> phân tích)
        if parsing_job is not None:
            steps.append(
                LineageStepSummary(
                    step=STEP_RAW,
                    label=STEP_LABELS[STEP_RAW],
                    available=True,
                    job_id=parsing_job.id,
                    status=parsing_job.status,
                    timestamp=parsing_job.received_at,
                )
            )
            parsed_records = self.parsed_record_repo.list_for_job(parsing_job.id)
            parsed = next((r for r in parsed_records if r.row_index == row_index), None)
            row_errors = [
                e
                for e in self.parsing_row_error_repo.list_for_job(parsing_job.id)
                if e.row_index == row_index
            ]
            steps.append(
                LineageStepSummary(
                    step=STEP_PARSING,
                    label=STEP_LABELS[STEP_PARSING],
                    available=parsed is not None,
                    job_id=parsing_job.id,
                    status=("LỖI" if row_errors else "OK") if parsed is not None else None,
                    timestamp=parsing_job.completed_at,
                    note=(
                        None
                        if parsed is not None
                        else "Không tìm thấy bản ghi đã phân tích cho dòng này"
                    ),
                )
            )
        else:
            steps.append(
                LineageStepSummary(
                    step=STEP_RAW, label=STEP_LABELS[STEP_RAW], available=False,
                    note="Không xác định được phiên phân tích (ParsingJob) gốc",
                )
            )
            steps.append(
                LineageStepSummary(
                    step=STEP_PARSING, label=STEP_LABELS[STEP_PARSING], available=False,
                    note="Không xác định được phiên phân tích (ParsingJob) gốc",
                )
            )

        # MAPPING
        if mapping_job is not None:
            mapped_records = self.mapped_record_repo.list_for_job(mapping_job.id)
            mapped = next((r for r in mapped_records if r.row_index == row_index), None)
            rejections = [
                r
                for r in self.mapping_rejection_repo.list_for_job(mapping_job.id)
                if r.row_index == row_index
            ]
            steps.append(
                LineageStepSummary(
                    step=STEP_MAPPING,
                    label=STEP_LABELS[STEP_MAPPING],
                    available=mapped is not None,
                    job_id=mapping_job.id,
                    status=("BỊ TỪ CHỐI" if rejections else "OK") if mapped is not None else (
                        "BỊ TỪ CHỐI" if rejections else None
                    ),
                    timestamp=mapping_job.completed_at,
                )
            )
        else:
            steps.append(
                LineageStepSummary(
                    step=STEP_MAPPING, label=STEP_LABELS[STEP_MAPPING], available=False,
                    note="Không xác định được phiên ánh xạ (MappingJob) gốc",
                )
            )

        # QUALITY
        if quality_job is not None:
            steps.append(
                LineageStepSummary(
                    step=STEP_QUALITY,
                    label=STEP_LABELS[STEP_QUALITY],
                    available=True,
                    job_id=quality_job.id,
                    status=quality_job.status,
                    timestamp=quality_job.completed_at,
                )
            )
        else:
            steps.append(
                LineageStepSummary(
                    step=STEP_QUALITY, label=STEP_LABELS[STEP_QUALITY], available=False,
                    note="Bản ghi curated chưa gắn quality_check_job_id",
                )
            )

        # PUBLISH: chính là bản ghi curated đang xem
        steps.append(
            LineageStepSummary(
                step=STEP_PUBLISH,
                label=STEP_LABELS[STEP_PUBLISH],
                available=True,
                job_id=dm.curated_publish_job_id,
                status=dm.publish_status,
                timestamp=dm.last_published_at,
            )
        )

        return LineageChain(
            curated_dm_record_id=dm.id,
            dataset_id=dm.dataset_id,
            row_index=dm.row_index,
            steps=steps,
        )

    # ---------- Bước 3: 'Xem chi tiết từng bước' ----------

    def get_step_detail(self, curated_dm_record_id: int, step: str) -> LineageStepDetail:
        step = (step or "").upper()
        if step not in LINEAGE_STEPS:
            raise InvalidLineageStep(step, LINEAGE_STEPS)

        dm, quality_job, mapping_job, parsing_job = self._load_context(curated_dm_record_id)
        row_index = dm.row_index
        label = STEP_LABELS[step]

        if step == STEP_RAW:
            if parsing_job is None:
                return LineageStepDetail(
                    step=step, label=label, available=False,
                    note="Không xác định được phiên phân tích (ParsingJob) gốc",
                )
            raw_rows = self.stg_row_repo.list_for_job(parsing_job.id)
            raw_row = raw_rows[row_index] if 0 <= row_index < len(raw_rows) else None
            return LineageStepDetail(
                step=step,
                label=label,
                available=raw_row is not None,
                input={
                    "raw_object_key": parsing_job.raw_object_key,
                    "source_format": parsing_job.source_format,
                    "ingestion_run_id": parsing_job.ingestion_run_id,
                    "data_source_id": parsing_job.data_source_id,
                },
                output=raw_row,
                transformation=(
                    "Hệ thống đọc dữ liệu thô từ tệp nguồn (MinIO, theo raw_object_key) "
                    "và lưu từng dòng vào bảng staging stg_structured_rows (UC-029 bước 2)."
                ),
                meta={
                    "parsing_job_id": parsing_job.id,
                    "dataset_id": parsing_job.dataset_id,
                    "row_index": row_index,
                },
            )

        if step == STEP_PARSING:
            if parsing_job is None:
                return LineageStepDetail(
                    step=step, label=label, available=False,
                    note="Không xác định được phiên phân tích (ParsingJob) gốc",
                )
            raw_rows = self.stg_row_repo.list_for_job(parsing_job.id)
            raw_row = raw_rows[row_index] if 0 <= row_index < len(raw_rows) else None
            parsed_records = self.parsed_record_repo.list_for_job(parsing_job.id)
            parsed = next((r for r in parsed_records if r.row_index == row_index), None)
            row_errors = [
                {"field_name": e.field_name, "message": e.message}
                for e in self.parsing_row_error_repo.list_for_job(parsing_job.id)
                if e.row_index == row_index
            ]
            return LineageStepDetail(
                step=step,
                label=label,
                available=parsed is not None,
                input=raw_row,
                output=parsed.mapped_fields if parsed is not None else None,
                transformation=(
                    "Ánh xạ tên trường theo lược đồ đích (schema_fields) -- dùng "
                    "field_mapping tường minh hoặc tự khớp tên cột đã chuẩn hoá -- "
                    "rồi ép kiểu dữ liệu theo data_type của từng trường (UC-029 bước 3-4)."
                ),
                meta={
                    "parsing_job_id": parsing_job.id,
                    "schema_fields": parsing_job.schema_fields,
                    "field_mapping": parsing_job.field_mapping,
                    "has_error": parsed.has_error if parsed is not None else None,
                    "row_errors": row_errors,
                },
                note=None if parsed is not None else "Không tìm thấy bản ghi đã phân tích cho dòng này",
            )

        if step == STEP_MAPPING:
            if mapping_job is None:
                return LineageStepDetail(
                    step=step, label=label, available=False,
                    note="Không xác định được phiên ánh xạ (MappingJob) gốc",
                )
            parsed_input = None
            if parsing_job is not None:
                parsed_records = self.parsed_record_repo.list_for_job(parsing_job.id)
                parsed = next((r for r in parsed_records if r.row_index == row_index), None)
                parsed_input = parsed.mapped_fields if parsed is not None else None
            mapped_records = self.mapped_record_repo.list_for_job(mapping_job.id)
            mapped = next((r for r in mapped_records if r.row_index == row_index), None)
            rejections = [
                {"field_name": r.field_name, "reason": r.reason}
                for r in self.mapping_rejection_repo.list_for_job(mapping_job.id)
                if r.row_index == row_index
            ]
            return LineageStepDetail(
                step=step,
                label=label,
                available=mapped is not None,
                input=parsed_input,
                output=mapped.standardized_fields if mapped is not None else None,
                transformation=(
                    "Áp dụng quy tắc ánh xạ trường sang dạng chuẩn (MappingRule kiểu "
                    "DIRECT: trim + đổi hoa/thường, hoặc CATALOG_LOOKUP: tra danh mục "
                    "chuẩn) cho từng trường; trường bắt buộc còn rỗng sau chuẩn hoá thì "
                    "cả dòng bị từ chối (UC-031 bước 1-2)."
                ),
                meta={
                    "mapping_job_id": mapping_job.id,
                    "dataset_id": mapping_job.dataset_id,
                    "rejections": rejections,
                },
                note=(
                    "Dòng này đã bị từ chối ở bước ánh xạ (trường bắt buộc rỗng)"
                    if rejections and mapped is None
                    else None
                ),
            )

        if step == STEP_QUALITY:
            if quality_job is None:
                return LineageStepDetail(
                    step=step, label=label, available=False,
                    note="Bản ghi curated chưa gắn quality_check_job_id",
                )
            mapped_input = None
            if mapping_job is not None:
                mapped_records = self.mapped_record_repo.list_for_job(mapping_job.id)
                mapped = next((r for r in mapped_records if r.row_index == row_index), None)
                mapped_input = mapped.standardized_fields if mapped is not None else None
            rule_results = [
                {
                    "rule_id": r.rule_id,
                    "rule_type": r.rule_type,
                    "field_names": r.field_names,
                    "total_checked": r.total_checked,
                    "failed_count": r.failed_count,
                    "pass_rate": r.pass_rate,
                }
                for r in self.quality_rule_result_repo.list_for_job(quality_job.id)
            ]
            published_records = self.quality_published_repo.list_for_job(quality_job.id)
            published = next((r for r in published_records if r.row_index == row_index), None)
            exception_items = self.quality_exception_repo.list_for_job(quality_job.id)
            exception_item = next(
                (r for r in exception_items if r.row_index == row_index), None
            )
            output = None
            outcome = None
            failed_rules = None
            if published is not None:
                output = published.standardized_fields
                outcome = "ĐẠT NGƯỠNG -- ĐÃ CÔNG BỐ"
            elif exception_item is not None:
                output = exception_item.standardized_fields
                outcome = f"DƯỚI NGƯỠNG -- HÀNG ĐỢI NGOẠI LỆ ({exception_item.status})"
                failed_rules = exception_item.failed_rules
            return LineageStepDetail(
                step=step,
                label=label,
                available=published is not None or exception_item is not None,
                input=mapped_input,
                output=output,
                transformation=(
                    "Chạy các quy tắc kiểm tra chất lượng đang áp dụng (đầy đủ/hợp lệ/"
                    "duy nhất/nhất quán), tính điểm theo từng nhóm quy tắc + điểm tổng "
                    "hợp, so với ngưỡng đạt (pass_threshold) -- đạt thì công bố, không "
                    "đạt thì đẩy vào hàng đợi ngoại lệ (UC-039 bước 1-3)."
                ),
                meta={
                    "quality_check_job_id": quality_job.id,
                    "overall_score": quality_job.overall_score,
                    "pass_threshold": quality_job.pass_threshold,
                    "rule_type_scores": quality_job.rule_type_scores,
                    "rule_results": rule_results,
                    "outcome": outcome,
                    "failed_rules": failed_rules,
                },
            )

        # STEP_PUBLISH
        quality_input = None
        if quality_job is not None:
            published_records = self.quality_published_repo.list_for_job(quality_job.id)
            published = next((r for r in published_records if r.row_index == row_index), None)
            if published is not None:
                quality_input = published.standardized_fields
            else:
                exception_items = self.quality_exception_repo.list_for_job(quality_job.id)
                exception_item = next(
                    (r for r in exception_items if r.row_index == row_index), None
                )
                if exception_item is not None and exception_item.status == "RESOLVED":
                    quality_input = exception_item.standardized_fields

        curated_publish_job = None
        if dm.curated_publish_job_id:
            curated_publish_job = self.curated_publish_job_repo.get_by_id(
                dm.curated_publish_job_id
            )
        batch_summary = None
        if curated_publish_job is not None:
            summaries = self.batch_summary_repo.list(
                dataset_id=dm.dataset_id, quality_check_job_id=dm.quality_check_job_id
            )
            batch_summary = next(
                (
                    s
                    for s in summaries
                    if s.curated_publish_job_id == curated_publish_job.id
                ),
                None,
            )

        return LineageStepDetail(
            step=STEP_PUBLISH,
            label=STEP_LABELS[STEP_PUBLISH],
            available=True,
            input=quality_input,
            output={
                "standardized_fields": dm.standardized_fields,
                "publish_status": dm.publish_status,
                "version": dm.version,
                "source": dm.source,
            },
            transformation=(
                "Chèn mới hoặc cập nhật tại chỗ (upsert theo dataset_id+row_index) vào "
                "kho chuẩn hoá dm_*, đặt publish_status=approved, tạo batch_summary + "
                "cập nhật độ mới dữ liệu, rồi phát sự kiện curated.published (UC-041 "
                "bước 1-4)."
            ),
            meta={
                "curated_dm_record_id": dm.id,
                "curated_publish_job_id": dm.curated_publish_job_id,
                "batch_summary": (
                    {
                        "id": batch_summary.id,
                        "records_received": batch_summary.records_received,
                        "inserted_count": batch_summary.inserted_count,
                        "updated_count": batch_summary.updated_count,
                        "created_at": batch_summary.created_at,
                    }
                    if batch_summary is not None
                    else None
                ),
                "first_published_at": dm.first_published_at,
                "last_published_at": dm.last_published_at,
            },
        )