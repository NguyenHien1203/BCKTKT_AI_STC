"""Application service UC-041: Công bố vào kho chuẩn hoá + batch_summary.

Đối chiếu docs/use_cases.json id=41: actor "Hệ thống tự động (Curated
Service)". Luồng nghiệp vụ:
1. Chèn/Cập nhật vào dm_*. Hệ thống lưu -- `CuratedDmRecordRepository`
   upsert theo khoá (`dataset_id`, `row_index`): dòng chưa từng công
   bố -> chèn mới; dòng đã công bố trước đó (ví dụ được UC-040 `FIX`
   sửa lại rồi công bố lại) -> cập nhật tại chỗ, tăng `version`.
2. Đặt `publish_status=approved`. Hệ thống cập nhật -- mọi
   `CuratedDmRecord` vừa chèn/cập nhật ở bước 1 đều được đánh dấu
   `publish_status="approved"` ngay (không có trạng thái chờ duyệt
   trung gian trong luồng tự động này).
3. Tạo `batch_summary` + cập nhật độ mới dữ liệu. Hệ thống ghi
   metadata -- 1 `CuratedBatchSummary` tóm tắt lượt công bố (số bản
   ghi nhận/chèn mới/cập nhật) + upsert `CuratedDatasetFreshness` của
   `dataset_id` (lần công bố gần nhất, tổng số bản ghi hiện có).
4. Kích hoạt sự kiện `curated.published`. Hệ thống phát sự kiện.

Toàn bộ chạy tự động, liền mạch trong 1 lần gọi `receive_and_process()`
-- nhận sự kiện `curated.publish.requested` (phát bởi UC-039 bước 3a
"Đạt ngưỡng -> công bố", hoặc UC-040 khi Phụ trách Dữ liệu chọn `FIX`
1 ngoại lệ chất lượng) rồi đọc lại các `QualityPublishedRecord` của
`quality_check_job_id` tương ứng -- cùng tinh thần
`QualityCheckService.receive_and_process()` / `FieldMappingService
.receive_and_process()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.domain.entities import (
    CuratedBatchSummary,
    CuratedDatasetFreshness,
    CuratedDmRecord,
    CuratedPublishJob,
)
from app.domain.exceptions import (
    CuratedPublishJobNotFound,
    NoPublishedRecordsToCurate,
    QualityCheckJobNotFoundForPublish,
)
from app.domain.repositories import (
    CuratedBatchSummaryRepository,
    CuratedDatasetFreshnessRepository,
    CuratedDmRecordRepository,
    CuratedPublishJobRepository,
    EventPublisher,
    QualityCheckJobRepository,
    QualityPublishedRecordRepository,
)

CURATED_PUBLISHED_EVENT = "curated.published"


@dataclass
class CuratedPublishResult:
    job: CuratedPublishJob
    dm_records: List[CuratedDmRecord] = field(default_factory=list)
    batch_summary: Optional[CuratedBatchSummary] = None
    freshness: Optional[CuratedDatasetFreshness] = None


class CuratedPublishService:
    def __init__(
        self,
        job_repo: CuratedPublishJobRepository,
        dm_record_repo: CuratedDmRecordRepository,
        batch_summary_repo: CuratedBatchSummaryRepository,
        freshness_repo: CuratedDatasetFreshnessRepository,
        published_record_repo: QualityPublishedRecordRepository,
        quality_check_job_repo: QualityCheckJobRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._jobs = job_repo
        self._dm_records = dm_record_repo
        self._batch_summaries = batch_summary_repo
        self._freshness = freshness_repo
        self._published_records = published_record_repo
        self._quality_check_jobs = quality_check_job_repo
        self._events = event_publisher

    # ---------- Nhận sự kiện `curated.publish.requested` + chạy trọn pipeline ----------

    def receive_and_process(
        self,
        quality_check_job_id: int,
        dataset_id: Optional[int] = None,
        mapping_job_id: Optional[int] = None,
        record_count: Optional[int] = None,
        source: str = "uc039_quality_check",
    ) -> CuratedPublishResult:
        quality_check_job = self._quality_check_jobs.get_by_id(quality_check_job_id)
        if quality_check_job is None:
            raise QualityCheckJobNotFoundForPublish(quality_check_job_id)

        resolved_dataset_id = dataset_id if dataset_id is not None else quality_check_job.dataset_id
        resolved_mapping_job_id = (
            mapping_job_id if mapping_job_id is not None else quality_check_job.mapping_job_id
        )

        job = CuratedPublishJob(
            id=None,
            quality_check_job_id=quality_check_job_id,
            dataset_id=resolved_dataset_id,
            mapping_job_id=resolved_mapping_job_id,
            source=source,
        )
        job = self._jobs.add(job)
        job.append_log(
            "INFO",
            f"Nhận sự kiện curated.publish.requested (quality_check_job_id="
            f"{quality_check_job_id}, source={source})",
        )
        job.start_running()
        self._jobs.update(job)

        records = self._published_records.list_for_job(quality_check_job_id)
        if not records:
            job.complete(
                status="FAILED",
                records_received=0,
                inserted_count=0,
                updated_count=0,
                error_message=str(NoPublishedRecordsToCurate(quality_check_job_id)),
            )
            job = self._jobs.update(job)
            return CuratedPublishResult(job=job)

        # ---------- Bước 1+2: Chèn/Cập nhật vào dm_* -- Đặt publish_status=approved ----------
        dm_records: List[CuratedDmRecord] = []
        inserted_count = 0
        updated_count = 0
        for r in records:
            existing = self._dm_records.get_by_dataset_and_row(resolved_dataset_id, r.row_index)
            if existing is None:
                dm_record = CuratedDmRecord(
                    id=None,
                    dataset_id=resolved_dataset_id,
                    row_index=r.row_index,
                    standardized_fields=dict(r.standardized_fields),
                    publish_status="approved",
                    version=1,
                    curated_publish_job_id=job.id,
                    quality_check_job_id=quality_check_job_id,
                    source=source,
                )
                dm_record = self._dm_records.add(dm_record)
                inserted_count += 1
            else:
                existing.apply_upsert(
                    standardized_fields=r.standardized_fields,
                    curated_publish_job_id=job.id,
                    quality_check_job_id=quality_check_job_id,
                    source=source,
                )
                dm_record = self._dm_records.update(existing)
                updated_count += 1
            dm_records.append(dm_record)

        job.append_log(
            "INFO",
            f"Chèn/Cập nhật vào dm_*: {inserted_count} bản ghi mới, {updated_count} bản ghi "
            f"cập nhật -- toàn bộ publish_status=approved",
        )

        # ---------- Bước 3: Tạo batch_summary + cập nhật độ mới dữ liệu ----------
        batch_summary = CuratedBatchSummary(
            id=None,
            curated_publish_job_id=job.id,
            dataset_id=resolved_dataset_id,
            quality_check_job_id=quality_check_job_id,
            mapping_job_id=resolved_mapping_job_id,
            source=source,
            records_received=len(records),
            inserted_count=inserted_count,
            updated_count=updated_count,
        )
        batch_summary = self._batch_summaries.add(batch_summary)

        freshness = self._freshness.get_by_dataset(resolved_dataset_id)
        if freshness is None:
            freshness = CuratedDatasetFreshness(
                id=None,
                dataset_id=resolved_dataset_id,
                last_batch_summary_id=batch_summary.id,
                last_published_at=batch_summary.created_at,
                total_published_records=len(records),
            )
        else:
            freshness.record_batch(
                batch_summary_id=batch_summary.id,
                record_count=len(records),
                published_at=batch_summary.created_at,
            )
        freshness = self._freshness.upsert(freshness)

        job.append_log(
            "INFO",
            f"Tạo batch_summary id={batch_summary.id} -- cập nhật độ mới dữ liệu "
            f"dataset_id={resolved_dataset_id} (tổng {freshness.total_published_records} "
            "bản ghi đã công bố)",
        )

        # ---------- Bước 4: Kích hoạt sự kiện curated.published ----------
        self._events.publish(
            CURATED_PUBLISHED_EVENT,
            {
                "curated_publish_job_id": job.id,
                "quality_check_job_id": quality_check_job_id,
                "dataset_id": resolved_dataset_id,
                "mapping_job_id": resolved_mapping_job_id,
                "batch_summary_id": batch_summary.id,
                "record_count": len(records),
                "inserted_count": inserted_count,
                "updated_count": updated_count,
                "source": source,
            },
        )
        job.append_log("INFO", "Đã phát sự kiện curated.published")

        job.complete(
            status="COMPLETED",
            records_received=len(records),
            inserted_count=inserted_count,
            updated_count=updated_count,
            batch_summary_id=batch_summary.id,
            published_event_published=True,
        )
        job = self._jobs.update(job)

        return CuratedPublishResult(
            job=job, dm_records=dm_records, batch_summary=batch_summary, freshness=freshness
        )

    # ---------- Tra cứu lại kết quả 1 lượt công bố ----------

    def get(self, curated_publish_job_id: int) -> CuratedPublishJob:
        job = self._jobs.get_by_id(curated_publish_job_id)
        if job is None:
            raise CuratedPublishJobNotFound(curated_publish_job_id)
        return job

    def list_jobs(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[CuratedPublishJob]:
        return self._jobs.list(
            dataset_id=dataset_id, quality_check_job_id=quality_check_job_id, status=status
        )

    def list_dm_records_for_job(self, curated_publish_job_id: int) -> List[CuratedDmRecord]:
        self.get(curated_publish_job_id)
        return self._dm_records.list_by_publish_job(curated_publish_job_id)

    def list_dm_records(
        self,
        dataset_id: Optional[int] = None,
        publish_status: Optional[str] = None,
    ) -> List[CuratedDmRecord]:
        """Xem kho chuẩn hoá (`dm_*`) -- lọc theo tập dữ liệu/`publish_status`."""
        return self._dm_records.list_by_dataset(dataset_id=dataset_id, publish_status=publish_status)

    def list_batch_summaries(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
    ) -> List[CuratedBatchSummary]:
        return self._batch_summaries.list(
            dataset_id=dataset_id, quality_check_job_id=quality_check_job_id
        )

    def get_dataset_freshness(self, dataset_id: Optional[int]) -> Optional[CuratedDatasetFreshness]:
        return self._freshness.get_by_dataset(dataset_id)

    def list_dataset_freshness(self) -> List[CuratedDatasetFreshness]:
        return self._freshness.list_all()