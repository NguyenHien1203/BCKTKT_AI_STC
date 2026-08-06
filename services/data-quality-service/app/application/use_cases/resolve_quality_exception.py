"""Application service UC-040: Xử lý ngoại lệ chất lượng.

Đối chiếu docs/use_cases.json id=40: actor "Phụ trách Dữ liệu" (khác
UC-039 là hệ thống tự động -- UC-040 là thao tác thủ công của con
người, đọc tiếp hàng đợi `QualityExceptionQueueItem` do UC-039 bước 3b
đẩy vào). Luồng nghiệp vụ:

1. Xem hàng đợi ngoại lệ. Hệ thống hiển thị.
   -> `list_queue()`: đọc `quality_exception_queue`, mặc định lọc
   `status=PENDING` (không giới hạn theo 1 lượt kiểm tra cụ thể).

2. Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn). Hệ thống lưu
   quyết định.
   -> `resolve_item()`:
     - `action=FIX`: sửa trực tiếp giá trị (các) trường bị lỗi
       (`corrected_fields`) -- merge vào `standardized_fields` hiện có
       của dòng (xem `QualityExceptionQueueItem.resolve()`), rồi công
       bố dòng đã sửa vào kho chuẩn hoá (tạo `QualityPublishedRecord`
       + phát sự kiện `curated.publish.requested`, cùng sự kiện UC-039
       bước 3a dùng để UC-041 đọc tiếp).
     - `action=REJECT`: từ chối dòng (không công bố), chỉ ghi nhận lý
       do + đánh dấu đã xử lý.
     - `action=REQUEST_SOURCE`: yêu cầu nguồn gửi lại dữ liệu -- không
       công bố, phát sự kiện `quality.exception.source_requested` (cho
       ingestion-service/đơn vị nguồn đọc tiếp, yêu cầu nộp lại).
   Cả 3 action đều ghi `resolution_reason`/`resolved_at` + đánh dấu
   `status=RESOLVED` qua `QualityExceptionQueueRepository.update()`.

3. Xử lý hàng loạt ngoại lệ cùng loại. Hệ thống áp dụng.
   -> `resolve_batch()`: áp dụng CÙNG 1 quyết định xử lý (action +
   corrected_fields/reason) cho TOÀN BỘ các dòng đang PENDING của 1
   `dataset_id` có ít nhất 1 quy tắc không đạt cùng `rule_type`
   (`QualityExceptionQueueItem.failed_rule_types()`), không cần xử lý
   từng dòng một qua bước 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.entities import QualityExceptionQueueItem, QualityPublishedRecord
from app.domain.exceptions import (
    InvalidQualityExceptionResolution,
    NoMatchingExceptionItemsForBatch,
    QualityExceptionQueueItemNotFound,
)
from app.domain.repositories import (
    EventPublisher,
    QualityExceptionQueueRepository,
    QualityPublishedRecordRepository,
)

CURATED_PUBLISH_REQUESTED_EVENT = "curated.publish.requested"
QUALITY_EXCEPTION_SOURCE_REQUESTED_EVENT = "quality.exception.source_requested"


@dataclass
class ResolveExceptionResult:
    item: QualityExceptionQueueItem
    published_record: Optional[QualityPublishedRecord] = None


@dataclass
class BatchResolveExceptionResult:
    items: List[QualityExceptionQueueItem] = field(default_factory=list)
    published_records: List[QualityPublishedRecord] = field(default_factory=list)


class QualityExceptionService:
    def __init__(
        self,
        queue_repo: QualityExceptionQueueRepository,
        published_repo: QualityPublishedRecordRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._queue = queue_repo
        self._published = published_repo
        self._events = event_publisher

    # ---------- Bước 1: Xem hàng đợi ngoại lệ ----------

    def list_queue(
        self, dataset_id: Optional[int] = None, status: Optional[str] = "PENDING"
    ) -> List[QualityExceptionQueueItem]:
        return self._queue.list_queue(dataset_id=dataset_id, status=status)

    def get(self, item_id: int) -> QualityExceptionQueueItem:
        item = self._queue.get_by_id(item_id)
        if item is None:
            raise QualityExceptionQueueItemNotFound(item_id)
        return item

    # ---------- Bước 2: Xử lý từng ngoại lệ ----------

    def resolve_item(
        self,
        item_id: int,
        action: str,
        corrected_fields: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> ResolveExceptionResult:
        item = self._queue.get_by_id(item_id)
        if item is None:
            raise QualityExceptionQueueItemNotFound(item_id)
        self._validate_request(item, action, corrected_fields, reason)

        try:
            item.resolve(action=action, corrected_fields=corrected_fields, reason=reason)
        except ValueError as exc:
            raise InvalidQualityExceptionResolution(str(exc)) from exc
        item = self._queue.update(item)

        published_record = self._apply_side_effects([item], action, reason)
        return ResolveExceptionResult(
            item=item, published_record=published_record[0] if published_record else None
        )

    # ---------- Bước 3: Xử lý hàng loạt ngoại lệ cùng loại ----------

    def resolve_batch(
        self,
        dataset_id: Optional[int],
        rule_type: str,
        action: str,
        corrected_fields: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> BatchResolveExceptionResult:
        if action not in QualityExceptionQueueItem.RESOLUTION_ACTIONS:
            raise InvalidQualityExceptionResolution(
                f"action phải thuộc {QualityExceptionQueueItem.RESOLUTION_ACTIONS}, "
                f"nhận '{action}'"
            )
        pending = self._queue.list_queue(dataset_id=dataset_id, status="PENDING")
        matching = [it for it in pending if rule_type in it.failed_rule_types()]
        if not matching:
            raise NoMatchingExceptionItemsForBatch(dataset_id, rule_type)

        resolved_items: List[QualityExceptionQueueItem] = []
        for it in matching:
            self._validate_request(it, action, corrected_fields, reason)
            try:
                it.resolve(action=action, corrected_fields=corrected_fields, reason=reason)
            except ValueError as exc:
                raise InvalidQualityExceptionResolution(str(exc)) from exc
            resolved_items.append(self._queue.update(it))

        published_records = self._apply_side_effects(resolved_items, action, reason)
        return BatchResolveExceptionResult(items=resolved_items, published_records=published_records)

    # ---------- Nội bộ ----------

    @staticmethod
    def _validate_request(
        item: QualityExceptionQueueItem,
        action: str,
        corrected_fields: Optional[Dict[str, Any]],
        reason: Optional[str],
    ) -> None:
        if item.status != "PENDING":
            raise InvalidQualityExceptionResolution(
                f"Ngoại lệ id={item.id} đã được xử lý trước đó (status={item.status})"
            )
        if action not in QualityExceptionQueueItem.RESOLUTION_ACTIONS:
            raise InvalidQualityExceptionResolution(
                f"action phải thuộc {QualityExceptionQueueItem.RESOLUTION_ACTIONS}, "
                f"nhận '{action}'"
            )
        if action == "FIX" and not corrected_fields:
            raise InvalidQualityExceptionResolution(
                "corrected_fields không được để trống khi action là FIX"
            )
        if action in ("REJECT", "REQUEST_SOURCE") and not (reason and reason.strip()):
            raise InvalidQualityExceptionResolution(
                "reason không được để trống khi action là REJECT hoặc REQUEST_SOURCE"
            )

    def _apply_side_effects(
        self,
        items: List[QualityExceptionQueueItem],
        action: str,
        reason: Optional[str],
    ) -> List[QualityPublishedRecord]:
        """Sau khi lưu quyết định (bước 2/3): `FIX` công bố (các) dòng

        đã sửa vào kho chuẩn hoá; `REQUEST_SOURCE` phát sự kiện yêu cầu
        nguồn gửi lại dữ liệu. `REJECT` không có tác dụng phụ nào khác
        ngoài việc đánh dấu đã xử lý."""
        published_records: List[QualityPublishedRecord] = []
        if action == "FIX":
            records = [
                QualityPublishedRecord(
                    id=None,
                    quality_check_job_id=it.quality_check_job_id,
                    dataset_id=it.dataset_id,
                    row_index=it.row_index,
                    standardized_fields=dict(it.standardized_fields),
                )
                for it in items
            ]
            published_records = self._published.add_many(records)
            self._events.publish(
                CURATED_PUBLISH_REQUESTED_EVENT,
                {
                    "quality_check_job_id": items[0].quality_check_job_id,
                    "dataset_id": items[0].dataset_id,
                    "record_count": len(published_records),
                    "source": "uc040_exception_fix",
                },
            )
        elif action == "REQUEST_SOURCE":
            self._events.publish(
                QUALITY_EXCEPTION_SOURCE_REQUESTED_EVENT,
                {
                    "dataset_id": items[0].dataset_id,
                    "quality_exception_item_ids": [it.id for it in items],
                    "row_indices": [it.row_index for it in items],
                    "reason": reason,
                },
            )
        return published_records