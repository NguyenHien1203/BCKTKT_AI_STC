"""Application service UC-034: Quản lý danh mục khoản mục NSNN.

Actor: "Quản trị Danh mục". Luồng nghiệp vụ:
1. Xem cây khoản mục NSNN (Chương / Loại / Khoản / Mục / Tiểu mục). Hệ
   thống hiển thị -- `get_tree(budget_year)`.
2. Thêm / Sửa entry. Hệ thống quản lý phiên bản theo năm ngân sách --
   `create_item()` / `update_item()` (tăng version + ghi lịch sử, trong
   phạm vi 1 `budget_year`). Khoản mục nhạy cảm (`is_sensitive=True`)
   KHÔNG được sửa trực tiếp bằng `update_item()`.
3. Đề nghị thay đổi khoản mục nhạy cảm. Hệ thống lưu yêu cầu chờ duyệt --
   `propose_change()` (chỉ áp dụng cho khoản mục `is_sensitive=True`),
   `approve_change()` / `reject_change()` cho người có thẩm quyền duyệt.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.domain.entities import (
    BudgetItemCatalogEntry,
    BudgetItemCatalogVersion,
    BudgetItemChangeRequest,
)
from app.domain.exceptions import (
    BudgetItemChangeRequestNotFound,
    BudgetItemCodeAlreadyExists,
    BudgetItemNotFound,
    BudgetItemSensitiveRequiresApproval,
    InvalidBudgetItem,
    InvalidBudgetItemChangeRequest,
)
from app.domain.repositories import (
    BudgetItemCatalogRepository,
    BudgetItemCatalogVersionRepository,
    BudgetItemChangeRequestRepository,
)


@dataclass
class BudgetItemTreeNode:
    item: BudgetItemCatalogEntry
    children: List["BudgetItemTreeNode"] = field(default_factory=list)


class BudgetItemCatalogService:
    def __init__(
        self,
        item_repo: BudgetItemCatalogRepository,
        version_repo: BudgetItemCatalogVersionRepository,
        change_request_repo: BudgetItemChangeRequestRepository,
    ) -> None:
        self._items = item_repo
        self._versions = version_repo
        self._change_requests = change_request_repo

    # ---------- Bước 1: Xem cây khoản mục NSNN ----------

    def list_items(
        self,
        budget_year: Optional[int] = None,
        parent_id: Optional[int] = "__unset__",
        level: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BudgetItemCatalogEntry]:
        return self._items.list(
            budget_year=budget_year, parent_id=parent_id, level=level, status=status
        )

    def get_tree(self, budget_year: int, include_closed: bool = True) -> List[BudgetItemTreeNode]:
        """Bước 1 'Hệ thống hiển thị': dựng cây Chương/Loại/Khoản/Mục/

        Tiểu mục của 1 năm ngân sách."""
        all_items = self._items.list_by_year(budget_year)
        if not include_closed:
            all_items = [i for i in all_items if i.is_active]

        by_parent: Dict[Optional[int], List[BudgetItemCatalogEntry]] = {}
        for it in all_items:
            by_parent.setdefault(it.parent_id, []).append(it)
        for children in by_parent.values():
            children.sort(key=lambda i: i.code)

        def build(parent_id: Optional[int]) -> List[BudgetItemTreeNode]:
            return [
                BudgetItemTreeNode(item=i, children=build(i.id))
                for i in by_parent.get(parent_id, [])
            ]

        return build(None)

    def get(self, item_id: int) -> BudgetItemCatalogEntry:
        item = self._items.get_by_id(item_id)
        if item is None:
            raise BudgetItemNotFound(item_id)
        return item

    def list_versions(self, item_id: int) -> List[BudgetItemCatalogVersion]:
        self.get(item_id)
        return self._versions.list_for_item(item_id)

    # ---------- Bước 2: Thêm / Sửa entry (quản lý phiên bản theo năm) ----------

    def create_item(
        self,
        code: str,
        name: str,
        level: str,
        budget_year: int,
        parent_id: Optional[int] = None,
        is_sensitive: bool = False,
        effective_from: Optional[str] = None,
        note: Optional[str] = None,
    ) -> BudgetItemCatalogEntry:
        """Bước 2 'Thêm entry' -- kiểm tra trùng mã trong CÙNG năm ngân

        sách + lưu phiên bản (version=1)."""
        code = code.strip()
        if self._items.get_by_code(code, budget_year) is not None:
            raise BudgetItemCodeAlreadyExists(code, budget_year)
        parent = None
        if parent_id is not None:
            parent = self._items.get_by_id(parent_id)
            if parent is None:
                raise InvalidBudgetItem(f"Khoản mục cha id={parent_id} không tồn tại")
            if parent.budget_year != budget_year:
                raise InvalidBudgetItem(
                    "Khoản mục cha phải cùng năm ngân sách với khoản mục con"
                )
            parent_levels = BudgetItemCatalogEntry.LEVELS
            if parent_levels.index(parent.level) >= parent_levels.index(level):
                raise InvalidBudgetItem(
                    f"Cấp '{level}' phải thấp hơn cấp của khoản mục cha ('{parent.level}')"
                )
        try:
            item = BudgetItemCatalogEntry(
                id=None,
                code=code,
                name=name.strip(),
                level=level,
                budget_year=budget_year,
                parent_id=parent_id,
                is_sensitive=is_sensitive,
                effective_from=effective_from,
                version=1,
            )
        except ValueError as exc:
            raise InvalidBudgetItem(str(exc)) from exc
        saved = self._items.add(item)
        self._record_version(saved, note)
        return saved

    def update_item(
        self,
        item_id: int,
        name: Optional[str] = None,
        status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> BudgetItemCatalogEntry:
        """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản theo năm ngân

        sách (tăng version + ghi lịch sử). Khoản mục nhạy cảm KHÔNG được
        sửa bằng hàm này -- phải dùng `propose_change()` (bước 3)."""
        item = self.get(item_id)
        if item.is_sensitive:
            raise BudgetItemSensitiveRequiresApproval(item_id)
        if item.status == "CLOSED":
            raise InvalidBudgetItem(f"Khoản mục id={item_id} đã đóng, không thể sửa")
        if name is not None:
            if not name.strip():
                raise InvalidBudgetItem("name không được để trống")
            item.name = name.strip()
        if status is not None:
            if status not in BudgetItemCatalogEntry.STATUSES:
                raise InvalidBudgetItem(
                    f"status phải thuộc {BudgetItemCatalogEntry.STATUSES}"
                )
            item.status = status
        item.bump_version()
        saved = self._items.update(item)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 3: Đề nghị thay đổi khoản mục nhạy cảm ----------

    def propose_change(
        self,
        item_id: int,
        requested_by: str,
        reason: str,
        proposed_name: Optional[str] = None,
        proposed_status: Optional[str] = None,
        proposed_is_sensitive: Optional[bool] = None,
    ) -> BudgetItemChangeRequest:
        """Bước 3 'Đề nghị thay đổi khoản mục nhạy cảm' -- hệ thống lưu

        yêu cầu chờ duyệt (KHÔNG áp dụng thay đổi ngay). Chỉ dùng cho
        khoản mục có `is_sensitive=True`."""
        item = self.get(item_id)
        if not item.is_sensitive:
            raise InvalidBudgetItemChangeRequest(
                f"Khoản mục id={item_id} không phải khoản mục nhạy cảm -- "
                "vui lòng sửa trực tiếp qua bước 2"
            )
        if proposed_status is not None and proposed_status not in BudgetItemCatalogEntry.STATUSES:
            raise InvalidBudgetItemChangeRequest(
                f"proposed_status phải thuộc {BudgetItemCatalogEntry.STATUSES}"
            )
        try:
            request = BudgetItemChangeRequest(
                id=None,
                item_id=item_id,
                budget_year=item.budget_year,
                requested_by=requested_by,
                reason=reason,
                proposed_name=proposed_name,
                proposed_status=proposed_status,
                proposed_is_sensitive=proposed_is_sensitive,
            )
        except ValueError as exc:
            raise InvalidBudgetItemChangeRequest(str(exc)) from exc
        return self._change_requests.add(request)

    def get_change_request(self, request_id: int) -> BudgetItemChangeRequest:
        request = self._change_requests.get_by_id(request_id)
        if request is None:
            raise BudgetItemChangeRequestNotFound(request_id)
        return request

    def list_change_requests(
        self, item_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[BudgetItemChangeRequest]:
        return self._change_requests.list(item_id=item_id, status=status)

    def approve_change(
        self, request_id: int, reviewed_by: str, review_note: Optional[str] = None
    ) -> BudgetItemCatalogEntry:
        """Duyệt yêu cầu -- áp dụng thay đổi vào khoản mục (tăng version +

        ghi lịch sử) và đóng yêu cầu ở trạng thái APPROVED."""
        request = self.get_change_request(request_id)
        item = self.get(request.item_id)
        try:
            request.approve(reviewed_by, review_note)
        except ValueError as exc:
            raise InvalidBudgetItemChangeRequest(str(exc)) from exc

        if request.proposed_name is not None:
            item.name = request.proposed_name
        if request.proposed_status is not None:
            item.status = request.proposed_status
        if request.proposed_is_sensitive is not None:
            item.is_sensitive = request.proposed_is_sensitive
        item.bump_version()
        saved_item = self._items.update(item)
        self._record_version(
            saved_item, f"Áp dụng theo yêu cầu duyệt id={request_id}: {request.reason}"
        )
        self._change_requests.update(request)
        return saved_item

    def reject_change(
        self, request_id: int, reviewed_by: str, review_note: Optional[str] = None
    ) -> BudgetItemChangeRequest:
        request = self.get_change_request(request_id)
        try:
            request.reject(reviewed_by, review_note)
        except ValueError as exc:
            raise InvalidBudgetItemChangeRequest(str(exc)) from exc
        return self._change_requests.update(request)

    # ---------- Nội bộ ----------

    def _record_version(
        self, item: BudgetItemCatalogEntry, note: Optional[str] = None
    ) -> None:
        self._versions.add(
            BudgetItemCatalogVersion(
                id=None,
                item_id=item.id,
                budget_year=item.budget_year,
                version=item.version,
                code=item.code,
                name=item.name,
                level=item.level,
                parent_id=item.parent_id,
                status=item.status,
                is_sensitive=item.is_sensitive,
                change_note=note,
            )
        )