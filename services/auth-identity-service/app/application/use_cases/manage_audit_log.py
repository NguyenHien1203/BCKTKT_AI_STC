"""Application layer — UC-09: Quản lý nhật ký truy cập và thao tác.

Đối chiếu docs/use_cases.json id=9: xem nhật ký toàn bộ, lọc theo tài khoản,
lọc theo thời gian, xuất báo cáo an toàn thông tin (ATTT) định kỳ dạng PDF.

Nhật ký (`AuditLogEntry`) là dữ liệu append-only: các UC khác (UC-01, UC-02,
UC-03...) ghi lại thao tác tạo/sửa/xoá qua `record()`; UC-09 chỉ đọc/lọc và
xuất báo cáo — không có nghiệp vụ sửa/xoá bản ghi nhật ký.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import AuditLogEntry
from app.domain.exceptions import InvalidAuditLogEntry, InvalidAuditLogFilter
from app.domain.repositories import AuditLogRepository, AuditReportGenerator


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLogService:
    def __init__(self, audit_repo: AuditLogRepository, report_generator: AuditReportGenerator):
        self._audit_logs = audit_repo
        self._reports = report_generator

    def record(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: str = "",
        detail: str = "",
        ip_address: str = "",
        status: str = "SUCCESS",
    ) -> AuditLogEntry:
        """Ghi 1 sự kiện vào nhật ký (dùng bởi các UC khác khi tạo/sửa/xoá dữ liệu nhạy cảm)."""
        try:
            entry = AuditLogEntry(
                id=None,
                username=username,
                action=action,
                resource_type=resource_type,
                created_at=_utc_now_iso(),
                resource_id=resource_id,
                detail=detail,
                ip_address=ip_address,
                status=status,
            )
        except ValueError as exc:
            raise InvalidAuditLogEntry(str(exc)) from exc
        return self._audit_logs.add(entry)

    @staticmethod
    def _validate_time_range(time_from: Optional[str], time_to: Optional[str]) -> None:
        if time_from and time_to and time_from > time_to:
            raise InvalidAuditLogFilter(
                "Thời gian bắt đầu (time_from) phải trước thời gian kết thúc (time_to)"
            )

    def list_logs(
        self,
        username: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AuditLogEntry]:
        """Xem nhật ký toàn bộ, hoặc lọc theo tài khoản và/hoặc theo khoảng thời gian."""
        self._validate_time_range(time_from, time_to)
        return self._audit_logs.list(username=username, time_from=time_from, time_to=time_to)

    def generate_security_report(
        self, time_from: Optional[str] = None, time_to: Optional[str] = None
    ) -> bytes:
        """Xuất báo cáo ATTT (an toàn thông tin) định kỳ dạng PDF cho khoảng thời gian đã chọn."""
        self._validate_time_range(time_from, time_to)
        entries = self._audit_logs.list(time_from=time_from, time_to=time_to)
        return self._reports.generate(entries, time_from, time_to, _utc_now_iso())