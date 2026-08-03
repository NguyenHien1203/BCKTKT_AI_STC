"""Application layer — UC-032: Xử lý hàng đợi chưa ánh xạ.

Đối chiếu docs/use_cases.json id=32: actor "Phụ trách Dữ liệu" (khác
UC-029/030/031 là hệ thống tự động — UC-032 là thao tác thủ công của
con người). Luồng nghiệp vụ:
1. Xem hàng đợi chưa ánh xạ. Hệ thống hiển thị.
   -> `list_queue()`: đọc `unmapped_value_queue` (bảng do UC-031 bước 3
   đẩy vào), mặc định lọc `status=PENDING`.
2. Xử lý giá trị (ánh xạ / tạo mục mới / từ chối). Hệ thống lưu mapping
   mới.
   -> `resolve_item()`:
     - `action=MAP`: ánh xạ giá trị nguồn (`raw_value`) sang 1 giá trị
       chuẩn đã tồn tại (hoặc do Phụ trách Dữ liệu tự gõ).
     - `action=CREATE_NEW`: tạo mục danh mục chuẩn mới cho giá trị này
       (cùng cơ chế lưu với MAP — khác biệt chỉ ở ý nghĩa nghiệp vụ, cả
       2 đều ghi 1 khoá mới vào `catalog_map`).
     - `action=REJECT`: từ chối giá trị (không đưa vào danh mục chuẩn,
       chỉ ghi nhận lý do + đánh dấu đã xử lý).
     - Với MAP/CREATE_NEW: hệ thống lưu mapping mới bằng cách tạo 1
       `MappingRule` phiên bản mới (CATALOG_LOOKUP, gắn `dataset_id` cụ
       thể để được ưu tiên áp dụng — xem
       `MappingRuleRepository.get_active_rules_for_dataset`), merge
       `catalog_map` hiện có của trường đó + thêm khoá
       `raw_value` (chuẩn hoá trim+upper) -> `resolved_value`. Từ lần
       chạy UC-031 tiếp theo, giá trị này sẽ tự ánh xạ được, không còn
       rơi vào hàng đợi.
3. Ánh xạ hàng loạt các giá trị tương tự. Hệ thống áp dụng đồng loạt.
   -> khi gọi `resolve_item(..., apply_to_similar=True)`: tìm các mục
   khác đang PENDING cùng `dataset_id`+`field_name`+giá trị nguồn (đã
   chuẩn hoá) trùng khớp `raw_value`, áp dụng cùng kết quả xử lý (dùng
   lại đúng 1 `MappingRule` mới tạo ở bước 2, không tạo thêm quy tắc).
"""
from dataclasses import dataclass
from typing import List, Optional

from app.domain.entities import MappingRule, UnmappedQueueItem
from app.domain.exceptions import (
    InvalidUnmappedQueueResolution,
    UnmappedQueueItemNotFound,
)
from app.domain.repositories import MappingRuleRepository, UnmappedQueueRepository


@dataclass
class ResolveResult:
    item: UnmappedQueueItem
    updated_rule: Optional[MappingRule]
    affected_items: List[UnmappedQueueItem]


class UnmappedQueueService:
    def __init__(
        self,
        queue_repo: UnmappedQueueRepository,
        rule_repo: MappingRuleRepository,
    ):
        self._queue = queue_repo
        self._rules = rule_repo

    # ---------- Bước 1: Xem hàng đợi chưa ánh xạ ----------

    def list_queue(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = "PENDING",
    ) -> List[UnmappedQueueItem]:
        return self._queue.list_queue(dataset_id=dataset_id, field_name=field_name, status=status)

    def get(self, item_id: int) -> UnmappedQueueItem:
        item = self._queue.get_by_id(item_id)
        if item is None:
            raise UnmappedQueueItemNotFound(item_id)
        return item

    # ---------- Bước 2-3: Xử lý giá trị + ánh xạ hàng loạt ----------

    def resolve_item(
        self,
        item_id: int,
        action: str,
        standard_value: Optional[str] = None,
        reason: Optional[str] = None,
        apply_to_similar: bool = False,
    ) -> ResolveResult:
        item = self._queue.get_by_id(item_id)
        if item is None:
            raise UnmappedQueueItemNotFound(item_id)
        if item.status != "PENDING":
            raise InvalidUnmappedQueueResolution(
                f"Giá trị id={item_id} đã được xử lý trước đó (status={item.status})"
            )
        if action not in UnmappedQueueItem.RESOLUTION_ACTIONS:
            raise InvalidUnmappedQueueResolution(
                f"action phải thuộc {UnmappedQueueItem.RESOLUTION_ACTIONS}, nhận '{action}'"
            )
        if action in ("MAP", "CREATE_NEW") and not (standard_value and standard_value.strip()):
            raise InvalidUnmappedQueueResolution(
                "standard_value không được để trống khi action là MAP hoặc CREATE_NEW"
            )
        if action == "REJECT" and not (reason and reason.strip()):
            raise InvalidUnmappedQueueResolution(
                "reason không được để trống khi action là REJECT"
            )

        updated_rule: Optional[MappingRule] = None
        if action in ("MAP", "CREATE_NEW"):
            # Bước 2 'Hệ thống lưu mapping mới': tạo phiên bản MappingRule
            # mới (CATALOG_LOOKUP) gắn dataset_id cụ thể của item để được
            # ưu tiên áp dụng ở các lần chạy UC-031 tiếp theo.
            updated_rule = self._save_new_mapping(item, standard_value.strip())

        try:
            item.resolve(
                action=action,
                resolved_value=standard_value.strip() if standard_value else None,
                reason=reason.strip() if reason else None,
            )
        except ValueError as exc:
            raise InvalidUnmappedQueueResolution(str(exc)) from exc
        item = self._queue.update(item)

        # Bước 3 'Ánh xạ hàng loạt các giá trị tương tự': áp dụng đồng
        # loạt cùng kết quả xử lý cho các mục PENDING khác cùng giá trị
        # nguồn (đã chuẩn hoá) của cùng trường + tập dữ liệu.
        affected_items: List[UnmappedQueueItem] = []
        if apply_to_similar:
            similar = self._queue.find_similar_pending(
                dataset_id=item.dataset_id,
                field_name=item.field_name,
                raw_value=item.raw_value,
                exclude_id=item.id,
            )
            for other in similar:
                try:
                    other.resolve(
                        action=action,
                        resolved_value=standard_value.strip() if standard_value else None,
                        reason=reason.strip() if reason else None,
                    )
                except ValueError:
                    continue
                affected_items.append(self._queue.update(other))

        return ResolveResult(item=item, updated_rule=updated_rule, affected_items=affected_items)

    def _save_new_mapping(self, item: UnmappedQueueItem, standard_value: str) -> MappingRule:
        rules = self._rules.get_active_rules_for_dataset(item.dataset_id)
        existing_rule = rules.get(item.field_name)

        catalog_map = {}
        if existing_rule is not None and existing_rule.rule_type == "CATALOG_LOOKUP":
            catalog_map = dict(existing_rule.catalog_map)
        key = item.lookup_key()
        catalog_map[key] = standard_value

        new_version = (existing_rule.version + 1) if existing_rule is not None else 1
        new_rule = MappingRule(
            id=None,
            field_name=item.field_name,
            version=new_version,
            rule_type="CATALOG_LOOKUP",
            dataset_id=item.dataset_id,
            catalog_map=catalog_map,
            is_active=True,
        )
        return self._rules.add(new_rule)