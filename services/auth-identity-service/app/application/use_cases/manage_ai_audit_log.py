"""Application layer — UC-10: Quản trị AI Audit Log.

Đối chiếu docs/use_cases.json id=10: xem danh sách AI query theo khoảng thời
gian, xem theo trace_id (toàn bộ chuỗi: prompt + phản hồi + nguồn + ảnh chụp
quyền + mô hình + phiên bản mẫu), lọc theo user_id, xuất báo cáo AI Audit
định kỳ tuần/tháng.

`AiAuditLogEntry` là dữ liệu append-only: UC-71/72/73 (AI hỏi đáp) ghi lại
mỗi phiên hỏi-đáp qua `record()`; UC-10 chỉ đọc/lọc/xuất báo cáo — không có
nghiệp vụ sửa/xoá bản ghi.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import AiAuditLogEntry
from app.domain.exceptions import (
    AiAuditLogNotFound,
    InvalidAiAuditLogEntry,
    InvalidAiAuditLogFilter,
)
from app.domain.repositories import AiAuditLogRepository, AiAuditReportGenerator

PERIODS = ("WEEK", "MONTH")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AiAuditLogService:
    def __init__(self, ai_audit_repo: AiAuditLogRepository, report_generator: AiAuditReportGenerator):
        self._ai_audit_logs = ai_audit_repo
        self._reports = report_generator

    def record(
        self,
        trace_id: str,
        username: str,
        model: str,
        prompt: str,
        response: str,
        sources: Optional[list] = None,
        permission_snapshot: Optional[dict] = None,
        prompt_version: str = "",
    ) -> AiAuditLogEntry:
        """Ghi 1 phiên hỏi-đáp AI vào nhật ký (dùng bởi UC-71/72/73 khi AI trả lời)."""
        try:
            entry = AiAuditLogEntry(
                id=None,
                trace_id=trace_id,
                username=username,
                model=model,
                prompt=prompt,
                response=response,
                created_at=_utc_now_iso(),
                sources=list(sources or []),
                permission_snapshot=dict(permission_snapshot or {}),
                prompt_version=prompt_version,
            )
        except ValueError as exc:
            raise InvalidAiAuditLogEntry(str(exc)) from exc
        return self._ai_audit_logs.add(entry)

    @staticmethod
    def _validate_time_range(time_from: Optional[str], time_to: Optional[str]) -> None:
        if time_from and time_to and time_from > time_to:
            raise InvalidAiAuditLogFilter(
                "Thời gian bắt đầu (time_from) phải trước thời gian kết thúc (time_to)"
            )

    def list_logs(
        self,
        user_id: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AiAuditLogEntry]:
        """Xem danh sách AI query theo khoảng thời gian, và/hoặc lọc theo user_id."""
        self._validate_time_range(time_from, time_to)
        return self._ai_audit_logs.list(user_id=user_id, time_from=time_from, time_to=time_to)

    def get_by_trace_id(self, trace_id: str) -> AiAuditLogEntry:
        """Xem toàn bộ chuỗi 1 phiên hỏi-đáp theo trace_id."""
        entry = self._ai_audit_logs.get_by_trace_id(trace_id)
        if entry is None:
            raise AiAuditLogNotFound(trace_id)
        return entry

    def generate_periodic_report(
        self,
        period: str,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> bytes:
        """Xuất báo cáo AI Audit định kỳ tuần/tháng cho khoảng thời gian đã chọn."""
        if period not in PERIODS:
            raise InvalidAiAuditLogFilter(
                f"Kỳ báo cáo '{period}' không hợp lệ — chỉ chấp nhận WEEK hoặc MONTH"
            )
        self._validate_time_range(time_from, time_to)
        entries = self._ai_audit_logs.list(time_from=time_from, time_to=time_to)
        return self._reports.generate(entries, period, time_from, time_to, _utc_now_iso())