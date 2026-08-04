"""Application service UC-036: Quản lý danh mục mặt hàng, loại văn bản,

nguồn vốn.

Actor: "Quản trị Danh mục". Luồng nghiệp vụ:
1. Xem từng danh mục (mặt hàng / loại văn bản / nguồn vốn). Hệ thống
   hiển thị -- `list_entries(catalog_type=...)`.
2. Thêm / Sửa entry. Hệ thống quản lý phiên bản -- `create_entry()` /
   `update_entry()` (tăng version + ghi lịch sử). Mục nhạy cảm
   (`is_sensitive=True`) KHÔNG được sửa trực tiếp bằng `update_entry()`.
3. Đề nghị thay đổi danh mục nhạy cảm. Hệ thống lưu yêu cầu chờ duyệt --
   `propose_change()` (chỉ áp dụng cho mục `is_sensitive=True`),
   `approve_change()` / `reject_change()` cho người có thẩm quyền duyệt
   (xem UC-037 "Phê duyệt thay đổi danh mục nhạy cảm").
"""
from typing import List, Optional

from app.domain.entities import CatalogChangeRequest, CatalogEntry, CatalogEntryVersion
from app.domain.exceptions import (
    CatalogChangeRequestNotFound,
    CatalogEntryCodeAlreadyExists,
    CatalogEntryNotFound,
    CatalogEntrySensitiveRequiresApproval,
    InvalidCatalogChangeRequest,
    InvalidCatalogEntry,
)
from app.domain.repositories import (
    CatalogChangeRequestRepository,
    CatalogEntryRepository,
    CatalogEntryVersionRepository,
)


class CatalogEntryService:
    def __init__(
        self,
        entry_repo: CatalogEntryRepository,
        version_repo: CatalogEntryVersionRepository,
        change_request_repo: CatalogChangeRequestRepository,
    ) -> None:
        self._entries = entry_repo
        self._versions = version_repo
        self._change_requests = change_request_repo

    # ---------- Bước 1: Xem từng danh mục ----------

    def list_entries(
        self,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogEntry]:
        """Bước 1 'Xem từng danh mục (mặt hàng / loại văn bản / nguồn

        vốn)' -- hệ thống hiển thị. Truyền `catalog_type` để xem riêng 1
        trong 3 danh mục, bỏ trống để xem toàn bộ."""
        return self._entries.list(catalog_type=catalog_type, status=status)

    def get(self, entry_id: int) -> CatalogEntry:
        entry = self._entries.get_by_id(entry_id)
        if entry is None:
            raise CatalogEntryNotFound(entry_id)
        return entry

    def list_versions(self, entry_id: int) -> List[CatalogEntryVersion]:
        self.get(entry_id)
        return self._versions.list_for_entry(entry_id)

    # ---------- Bước 2: Thêm / Sửa entry (hệ thống quản lý phiên bản) ----------

    def create_entry(
        self,
        catalog_type: str,
        code: str,
        name: str,
        unit: Optional[str] = None,
        description: Optional[str] = None,
        is_sensitive: bool = False,
        effective_from: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CatalogEntry:
        """Bước 2 'Thêm entry' -- kiểm tra trùng mã trong CÙNG

        `catalog_type` + lưu phiên bản (version=1)."""
        code = code.strip()
        if self._entries.get_by_code(code, catalog_type) is not None:
            raise CatalogEntryCodeAlreadyExists(code, catalog_type)
        try:
            entry = CatalogEntry(
                id=None,
                catalog_type=catalog_type,
                code=code,
                name=name.strip(),
                unit=unit.strip() if unit else None,
                description=description.strip() if description else None,
                is_sensitive=is_sensitive,
                effective_from=effective_from,
                version=1,
            )
        except ValueError as exc:
            raise InvalidCatalogEntry(str(exc)) from exc
        saved = self._entries.add(entry)
        self._record_version(saved, note)
        return saved

    def update_entry(
        self,
        entry_id: int,
        name: Optional[str] = None,
        unit: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CatalogEntry:
        """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản (tăng version

        + ghi lịch sử). Mục nhạy cảm KHÔNG được sửa bằng hàm này -- phải
        dùng `propose_change()` (bước 3)."""
        entry = self.get(entry_id)
        if entry.is_sensitive:
            raise CatalogEntrySensitiveRequiresApproval(entry_id)
        if entry.status == "CLOSED":
            raise InvalidCatalogEntry(f"Mục id={entry_id} đã đóng, không thể sửa")
        if name is not None:
            if not name.strip():
                raise InvalidCatalogEntry("name không được để trống")
            entry.name = name.strip()
        if unit is not None:
            entry.unit = unit.strip() or None
        if description is not None:
            entry.description = description.strip() or None
        if status is not None:
            if status not in CatalogEntry.STATUSES:
                raise InvalidCatalogEntry(f"status phải thuộc {CatalogEntry.STATUSES}")
            entry.status = status
        entry.bump_version()
        saved = self._entries.update(entry)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 3: Đề nghị thay đổi danh mục nhạy cảm ----------

    def propose_change(
        self,
        entry_id: int,
        requested_by: str,
        reason: str,
        proposed_name: Optional[str] = None,
        proposed_unit: Optional[str] = None,
        proposed_description: Optional[str] = None,
        proposed_status: Optional[str] = None,
        proposed_is_sensitive: Optional[bool] = None,
    ) -> CatalogChangeRequest:
        """Bước 3 'Đề nghị thay đổi danh mục nhạy cảm' -- hệ thống lưu

        yêu cầu chờ duyệt (KHÔNG áp dụng thay đổi ngay). Chỉ dùng cho mục
        có `is_sensitive=True`."""
        entry = self.get(entry_id)
        if not entry.is_sensitive:
            raise InvalidCatalogChangeRequest(
                f"Mục id={entry_id} không phải mục nhạy cảm -- vui lòng sửa trực tiếp qua bước 2"
            )
        if proposed_status is not None and proposed_status not in CatalogEntry.STATUSES:
            raise InvalidCatalogChangeRequest(
                f"proposed_status phải thuộc {CatalogEntry.STATUSES}"
            )
        try:
            request = CatalogChangeRequest(
                id=None,
                entry_id=entry_id,
                catalog_type=entry.catalog_type,
                requested_by=requested_by,
                reason=reason,
                proposed_name=proposed_name,
                proposed_unit=proposed_unit,
                proposed_description=proposed_description,
                proposed_status=proposed_status,
                proposed_is_sensitive=proposed_is_sensitive,
            )
        except ValueError as exc:
            raise InvalidCatalogChangeRequest(str(exc)) from exc
        return self._change_requests.add(request)

    def get_change_request(self, request_id: int) -> CatalogChangeRequest:
        request = self._change_requests.get_by_id(request_id)
        if request is None:
            raise CatalogChangeRequestNotFound(request_id)
        return request

    def list_change_requests(
        self,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogChangeRequest]:
        return self._change_requests.list(
            entry_id=entry_id, catalog_type=catalog_type, status=status
        )

    def approve_change(
        self, request_id: int, reviewed_by: str, review_note: Optional[str] = None
    ) -> CatalogEntry:
        """Duyệt yêu cầu -- áp dụng thay đổi vào mục danh mục (tăng

        version + ghi lịch sử) và đóng yêu cầu ở trạng thái APPROVED.
        (Dùng bởi UC-037 "Phê duyệt thay đổi danh mục nhạy cảm".)"""
        request = self.get_change_request(request_id)
        entry = self.get(request.entry_id)
        try:
            request.approve(reviewed_by, review_note)
        except ValueError as exc:
            raise InvalidCatalogChangeRequest(str(exc)) from exc

        if request.proposed_name is not None:
            entry.name = request.proposed_name
        if request.proposed_unit is not None:
            entry.unit = request.proposed_unit
        if request.proposed_description is not None:
            entry.description = request.proposed_description
        if request.proposed_status is not None:
            entry.status = request.proposed_status
        if request.proposed_is_sensitive is not None:
            entry.is_sensitive = request.proposed_is_sensitive
        entry.bump_version()
        saved_entry = self._entries.update(entry)
        self._record_version(
            saved_entry, f"Áp dụng theo yêu cầu duyệt id={request_id}: {request.reason}"
        )
        self._change_requests.update(request)
        return saved_entry

    def reject_change(
        self, request_id: int, reviewed_by: str, review_note: Optional[str] = None
    ) -> CatalogChangeRequest:
        request = self.get_change_request(request_id)
        try:
            request.reject(reviewed_by, review_note)
        except ValueError as exc:
            raise InvalidCatalogChangeRequest(str(exc)) from exc
        return self._change_requests.update(request)

    # ---------- Nội bộ ----------

    def _record_version(self, entry: CatalogEntry, note: Optional[str] = None) -> None:
        self._versions.add(
            CatalogEntryVersion(
                id=None,
                entry_id=entry.id,
                catalog_type=entry.catalog_type,
                version=entry.version,
                code=entry.code,
                name=entry.name,
                unit=entry.unit,
                status=entry.status,
                is_sensitive=entry.is_sensitive,
                change_note=note,
            )
        )