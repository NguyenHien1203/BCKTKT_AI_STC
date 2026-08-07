"""UC-046: Xuất báo cáo nguồn gốc dữ liệu (docs/use_cases.json id=46).

Actor: "Kiểm toán viên". Luồng nghiệp vụ:
1. Chọn phạm vi (tập dữ liệu / bản ghi / nguồn). Hệ thống hiển thị.
2. Sinh báo cáo nguồn gốc dữ liệu. Hệ thống kết xuất PDF.
3. Kết xuất PDF. Hệ thống trả file.

Đây là use case CHỈ ĐỌC (read-only) -- không tạo bảng mới, không thay
đổi dữ liệu. Tái sử dụng NGUYÊN VẸN `RecordLineageService` của UC-045
(truy vết 1 bản ghi curated qua 5 bước RAW -> PARSING -> MAPPING ->
QUALITY -> PUBLISH) làm lõi, chỉ bổ sung tầng "chọn phạm vi" để gộp
nhiều bản ghi vào 1 báo cáo:

- DATASET (tập dữ liệu): toàn bộ bản ghi curated (`dm_*`) của 1
  `dataset_id`.
- RECORD (bản ghi): đúng 1 bản ghi curated theo `curated_dm_record_id`
  -- báo cáo kèm chi tiết đầy đủ từng bước (dữ liệu vào/ra + phép biến
  đổi, giống UC-045 bước 3).
- SOURCE (nguồn): toàn bộ bản ghi curated thuộc các `dataset_id` có ít
  nhất 1 `ParsingJob` gắn `data_source_id` tương ứng (đã được lưu kèm
  theo sự kiện `parsing.requested`, xem `ParsingJob.data_source_id`).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.application.use_cases.trace_record_lineage import (
    LineageChain,
    LineageStepDetail,
    RecordLineageService,
)
from app.domain.entities import CuratedDmRecord
from app.domain.exceptions import (
    CuratedDmRecordNotFound,
    InvalidProvenanceReportScope,
    ProvenanceReportScopeNotFound,
)
from app.domain.repositories import CuratedDmRecordRepository, ParsingJobRepository

SCOPE_DATASET = "DATASET"
SCOPE_RECORD = "RECORD"
SCOPE_SOURCE = "SOURCE"

SCOPE_TYPES = (SCOPE_DATASET, SCOPE_RECORD, SCOPE_SOURCE)

SCOPE_LABELS = {
    SCOPE_DATASET: "Tập dữ liệu",
    SCOPE_RECORD: "Bản ghi",
    SCOPE_SOURCE: "Nguồn dữ liệu",
}

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProvenanceReportRecord:
    """1 bản ghi trong báo cáo -- chuỗi nguồn gốc (bước 2) + tuỳ chọn

    chi tiết từng bước (bước 3, chỉ bật khi phạm vi RECORD hoặc khi
    người dùng chủ động yêu cầu)."""

    curated_dm_record_id: int
    dataset_id: Optional[int]
    row_index: int
    publish_status: str
    version: int
    chain: LineageChain
    step_details: Optional[List[LineageStepDetail]] = None


@dataclass
class ProvenanceReport:
    scope_type: str
    scope_label: str
    scope_value: str
    generated_at: str = field(default_factory=_utc_now_iso)
    total_matched: int = 0
    returned_count: int = 0
    truncated: bool = False
    fully_traced_count: int = 0
    records: List[ProvenanceReportRecord] = field(default_factory=list)


class DataProvenanceReportService:
    def __init__(
        self,
        lineage_service: RecordLineageService,
        dm_record_repo: CuratedDmRecordRepository,
        parsing_job_repo: ParsingJobRepository,
    ) -> None:
        self.lineage_service = lineage_service
        self.dm_record_repo = dm_record_repo
        self.parsing_job_repo = parsing_job_repo

    # ---------- Bước 1 'Chọn phạm vi' ----------

    @staticmethod
    def _parse_scope_value_as_int(scope_type: str, scope_value: str) -> int:
        try:
            return int(str(scope_value).strip())
        except (TypeError, ValueError):
            raise InvalidProvenanceReportScope(
                f"Giá trị phạm vi '{scope_value}' không hợp lệ cho loại {scope_type} "
                "-- phải là số nguyên (id)"
            )

    def _resolve_records(self, scope_type: str, scope_value: str) -> List[CuratedDmRecord]:
        scope_type = (scope_type or "").upper().strip()
        if scope_type not in SCOPE_TYPES:
            raise InvalidProvenanceReportScope(
                f"Loại phạm vi '{scope_type}' không hợp lệ, phải thuộc {list(SCOPE_TYPES)}"
            )

        if scope_type == SCOPE_RECORD:
            curated_dm_record_id = self._parse_scope_value_as_int(scope_type, scope_value)
            record = self.dm_record_repo.get_by_id(curated_dm_record_id)
            if record is None:
                raise CuratedDmRecordNotFound(curated_dm_record_id)
            return [record]

        if scope_type == SCOPE_DATASET:
            dataset_id = self._parse_scope_value_as_int(scope_type, scope_value)
            records = self.dm_record_repo.list_by_dataset(dataset_id=dataset_id)
            if not records:
                raise ProvenanceReportScopeNotFound(scope_type, str(scope_value))
            return records

        # SCOPE_SOURCE: gián tiếp qua ParsingJob.data_source_id -> dataset_id
        data_source_id = self._parse_scope_value_as_int(scope_type, scope_value)
        parsing_jobs = self.parsing_job_repo.list()
        dataset_ids = sorted(
            {
                job.dataset_id
                for job in parsing_jobs
                if job.data_source_id == data_source_id and job.dataset_id is not None
            }
        )
        if not dataset_ids:
            raise ProvenanceReportScopeNotFound(scope_type, str(scope_value))

        records: List[CuratedDmRecord] = []
        seen_ids = set()
        for dataset_id in dataset_ids:
            for record in self.dm_record_repo.list_by_dataset(dataset_id=dataset_id):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    records.append(record)
        if not records:
            raise ProvenanceReportScopeNotFound(scope_type, str(scope_value))
        return records

    # ---------- Bước 2 'Sinh báo cáo nguồn gốc dữ liệu' ----------

    def build_report(
        self,
        scope_type: str,
        scope_value: str,
        limit: Optional[int] = None,
        include_step_details: Optional[bool] = None,
    ) -> ProvenanceReport:
        all_records = self._resolve_records(scope_type, scope_value)
        scope_type = scope_type.upper().strip()

        effective_limit = limit if limit else DEFAULT_LIMIT
        effective_limit = max(1, min(effective_limit, MAX_LIMIT))

        total_matched = len(all_records)
        # mới nhất (id lớn hơn) trước, dễ đọc hơn cho báo cáo kiểm toán
        all_records = sorted(all_records, key=lambda r: (r.dataset_id or 0, r.row_index))
        truncated = total_matched > effective_limit
        selected = all_records[:effective_limit]

        # Mặc định chỉ lấy chi tiết đầy đủ từng bước khi phạm vi là 1 bản ghi
        # duy nhất (RECORD) -- tránh báo cáo DATASET/SOURCE quá nặng. Người
        # dùng có thể chủ động bật `include_step_details=True`.
        want_details = (
            include_step_details if include_step_details is not None else (scope_type == SCOPE_RECORD)
        )

        report_records: List[ProvenanceReportRecord] = []
        fully_traced_count = 0
        for record in selected:
            chain = self.lineage_service.get_chain(record.id)
            if all(step.available for step in chain.steps):
                fully_traced_count += 1
            step_details: Optional[List[LineageStepDetail]] = None
            if want_details:
                step_details = [
                    self.lineage_service.get_step_detail(record.id, step.step)
                    for step in chain.steps
                ]
            report_records.append(
                ProvenanceReportRecord(
                    curated_dm_record_id=record.id,
                    dataset_id=record.dataset_id,
                    row_index=record.row_index,
                    publish_status=record.publish_status,
                    version=record.version,
                    chain=chain,
                    step_details=step_details,
                )
            )

        return ProvenanceReport(
            scope_type=scope_type,
            scope_label=SCOPE_LABELS[scope_type],
            scope_value=str(scope_value),
            total_matched=total_matched,
            returned_count=len(report_records),
            truncated=truncated,
            fully_traced_count=fully_traced_count,
            records=report_records,
        )