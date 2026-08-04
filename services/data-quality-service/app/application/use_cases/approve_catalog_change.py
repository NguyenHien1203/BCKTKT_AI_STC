"""Application service UC-037: Phê duyệt thay đổi danh mục nhạy cảm.

Actor: "Lãnh đạo Phòng nghiệp vụ Sở Tài chính". Luồng nghiệp vụ:
1. Xem các yêu cầu chờ duyệt -- `list_pending_requests()`.
2. Hệ thống hiển thị diff -- `get_diff()` (so sánh giá trị hiện tại của
   mục danh mục với các trường được đề nghị thay đổi ở UC-036 bước 3).
3. Phê duyệt / từ chối -- `approve()` / `reject()`.
4. Hệ thống cập nhật và áp dụng thay đổi -- `approve()` gọi lại
   `CatalogEntryService.approve_change()` (đã có từ UC-036) để áp dụng
   thay đổi vào `CatalogEntry` + tăng version + ghi lịch sử phiên bản.
5. Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký -- MỌI quyết định
   (phê duyệt lẫn từ chối) đều BẮT BUỘC kèm `reason` và được ghi lại
   thành 1 `CatalogChangeAuditLog` append-only, kèm `diff_snapshot` chụp
   lại đúng nội dung diff tại thời điểm quyết định (`list_audit_logs()`
   để tra cứu lại nhật ký).

Dùng lại nguyên vẹn `CatalogEntryService` (UC-036) thay vì viết lại
logic áp dụng thay đổi -- UC-037 chỉ bổ sung: bắt buộc lý do, hiển thị
diff, và ghi nhật ký riêng (khác `review_note` vốn tuỳ chọn ở UC-036).
"""
from typing import List, Optional

from app.application.use_cases.manage_catalog_entry import CatalogEntryService
from app.domain.entities import CatalogChangeAuditLog, CatalogChangeRequest, CatalogEntry
from app.domain.exceptions import InvalidCatalogChangeApproval
from app.domain.repositories import CatalogChangeAuditLogRepository

# Các trường có thể được đề nghị thay đổi (UC-036 bước 3) -- dùng để dựng
# diff theo đúng thứ tự hiển thị và để tra nhãn tiếng Việt hiển thị lên UI.
_DIFF_FIELDS = [
    ("name", "Tên"),
    ("unit", "Đơn vị tính"),
    ("description", "Mô tả"),
    ("status", "Trạng thái"),
    ("is_sensitive", "Mục nhạy cảm"),
]


class CatalogChangeApprovalService:
    def __init__(
        self,
        catalog_entry_service: CatalogEntryService,
        audit_log_repo: CatalogChangeAuditLogRepository,
    ) -> None:
        self._catalog_entries = catalog_entry_service
        self._audit_logs = audit_log_repo

    # ---------- Bước 1: Xem các yêu cầu chờ duyệt ----------

    def list_pending_requests(
        self, catalog_type: Optional[str] = None
    ) -> List[CatalogChangeRequest]:
        """Bước 1 'Xem các yêu cầu chờ duyệt' -- chỉ lấy các yêu cầu

        `status=PENDING` (mặc định của bước 3 UC-036), có thể lọc thêm
        theo `catalog_type` (ITEM/DOCUMENT_TYPE/FUNDING_SOURCE)."""
        return self._catalog_entries.list_change_requests(
            catalog_type=catalog_type, status="PENDING"
        )

    # ---------- Bước 2: Hệ thống hiển thị diff ----------

    def build_diff(self, request: CatalogChangeRequest, entry: CatalogEntry) -> List[dict]:
        """Bước 2 'Hệ thống hiển thị diff' -- so sánh giá trị HIỆN TẠI

        của mục danh mục (`entry`) với từng trường được đề nghị thay đổi
        trong `request`. Chỉ trả về các trường THỰC SỰ được đề nghị (bỏ
        qua trường không đổi -- `proposed_<field> is None`)."""
        proposed = {
            "name": request.proposed_name,
            "unit": request.proposed_unit,
            "description": request.proposed_description,
            "status": request.proposed_status,
            "is_sensitive": request.proposed_is_sensitive,
        }
        diff = []
        for field_name, field_label in _DIFF_FIELDS:
            new_value = proposed[field_name]
            if new_value is None:
                continue
            old_value = getattr(entry, field_name)
            diff.append(
                {
                    "field": field_name,
                    "field_label": field_label,
                    "old_value": old_value,
                    "new_value": new_value,
                    "changed": old_value != new_value,
                }
            )
        return diff

    def get_diff(self, request_id: int) -> dict:
        """Bước 2 'Hệ thống hiển thị diff' cho 1 yêu cầu cụ thể -- gồm

        thông tin mục danh mục đang xét + danh sách thay đổi đề nghị."""
        request = self._catalog_entries.get_change_request(request_id)
        entry = self._catalog_entries.get(request.entry_id)
        return {
            "request": request,
            "entry": entry,
            "changes": self.build_diff(request, entry),
        }

    # ---------- Bước 3 + 4 + 5: Phê duyệt / từ chối -- áp dụng -- ghi nhật ký ----------

    def approve(self, request_id: int, decided_by: str, reason: str) -> dict:
        """Bước 3 'Phê duyệt' -- bước 4 'Hệ thống cập nhật và áp dụng

        thay đổi' (dùng lại `CatalogEntryService.approve_change()` của
        UC-036) -- bước 5 'Ghi lý do phê duyệt -- Hệ thống lưu vào nhật
        ký' (bắt buộc `reason`, khác `review_note` tuỳ chọn của UC-036).
        """
        self._require_reason(reason)
        diff_info = self.get_diff(request_id)
        updated_entry = self._catalog_entries.approve_change(
            request_id, reviewed_by=decided_by, review_note=reason
        )
        log = self._write_audit_log(
            request_id=request_id,
            entry_id=updated_entry.id,
            catalog_type=updated_entry.catalog_type,
            action="APPROVED",
            decided_by=decided_by,
            reason=reason,
            diff=diff_info["changes"],
        )
        return {"entry": updated_entry, "audit_log": log}

    def reject(self, request_id: int, decided_by: str, reason: str) -> dict:
        """Bước 3 'Từ chối' -- KHÔNG áp dụng thay đổi -- bước 5 'Ghi lý

        do phê duyệt -- Hệ thống lưu vào nhật ký' (bắt buộc `reason`)."""
        self._require_reason(reason)
        diff_info = self.get_diff(request_id)
        rejected_request = self._catalog_entries.reject_change(
            request_id, reviewed_by=decided_by, review_note=reason
        )
        log = self._write_audit_log(
            request_id=request_id,
            entry_id=rejected_request.entry_id,
            catalog_type=rejected_request.catalog_type,
            action="REJECTED",
            decided_by=decided_by,
            reason=reason,
            diff=diff_info["changes"],
        )
        return {"request": rejected_request, "audit_log": log}

    # ---------- Bước 5: tra cứu nhật ký ----------

    def list_audit_logs(
        self,
        request_id: Optional[int] = None,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[CatalogChangeAuditLog]:
        return self._audit_logs.list(
            request_id=request_id, entry_id=entry_id, catalog_type=catalog_type, action=action
        )

    # ---------- Nội bộ ----------

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise InvalidCatalogChangeApproval(
                "Phải ghi lý do phê duyệt/từ chối trước khi lưu vào nhật ký (bước 4 UC-037)"
            )

    def _write_audit_log(
        self,
        request_id: int,
        entry_id: int,
        catalog_type: str,
        action: str,
        decided_by: str,
        reason: str,
        diff: List[dict],
    ) -> CatalogChangeAuditLog:
        import json

        log = CatalogChangeAuditLog(
            id=None,
            request_id=request_id,
            entry_id=entry_id,
            catalog_type=catalog_type,
            action=action,
            decided_by=decided_by,
            decision_reason=reason,
            diff_snapshot=json.dumps(diff, ensure_ascii=False),
        )
        return self._audit_logs.add(log)