"""Application layer — UC-027: Đối soát phiên intake.

Đối chiếu docs/use_cases.json id=27: actor "Quản trị Tích hợp, Phụ trách
Dữ liệu". Luồng nghiệp vụ:
1. Chọn phiên cần đối soát -> hệ thống mở 1 phiên đối soát
   (`IntakeReconciliation`) gắn với 1 `TabmisIntakeSession` (UC-022/023).
   Nếu phiên tiếp nhận đó đã có 1 lượt đối soát đang mở (OPEN) thì tái sử
   dụng, không tạo trùng.
2. Hệ thống hiển thị tổng kiểm soát -> chụp lại (snapshot) `control_totals`
   của phiên tiếp nhận tại thời điểm mở đối soát.
3. Đánh dấu phát hiện thiếu/sai -> ghi nhận 1 phát hiện (MISSING/INCORRECT).
4. Hệ thống lưu -> phát hiện được lưu ngay vào repository.
5. Đóng phiên đối soát đạt yêu cầu -> chỉ cho phép đóng khi không còn phát
   hiện nào ở trạng thái OPEN (mọi thiếu/sai đã được xử lý xong).
6. Hệ thống cập nhật trạng thái -> `status` chuyển OPEN -> CLOSED.

Không tạo lại hạ tầng "phiên tiếp nhận" — tái sử dụng
`TabmisIntakeSessionRepository` (UC-022/023) để lấy `control_totals` làm
tổng kiểm soát hiển thị ở bước 2; mỗi lượt đối soát được ghi lại vào
`intake_reconciliations` (`IntakeReconciliationRepository`) để tra cứu lịch
sử.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import IntakeReconciliation
from app.domain.exceptions import (
    IntakeReconciliationAlreadyClosed,
    IntakeReconciliationFindingNotFound,
    IntakeReconciliationHasUnresolvedFindings,
    IntakeReconciliationNotFound,
    InvalidIntakeReconciliation,
    TabmisIntakeSessionNotFound,
)
from app.domain.repositories import IntakeReconciliationRepository, TabmisIntakeSessionRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IntakeReconciliationService:
    def __init__(
        self,
        reconciliation_repo: IntakeReconciliationRepository,
        session_repo: TabmisIntakeSessionRepository,
    ):
        self._reconciliations = reconciliation_repo
        self._sessions = session_repo

    def _get_session(self, session_id: int):
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise TabmisIntakeSessionNotFound(session_id)
        return session

    # ---------- Bước 1-2: Chọn phiên cần đối soát -> hiển thị tổng kiểm soát ----------

    def open_or_get(self, session_id: int, reconciled_by: str) -> IntakeReconciliation:
        """Chọn phiên cần đối soát: nếu phiên tiếp nhận đã có 1 lượt đối
        soát đang mở thì trả về lượt đó (không tạo trùng); nếu chưa, hệ
        thống mở 1 phiên đối soát mới, snapshot `control_totals` của phiên
        tiếp nhận để hiển thị tổng kiểm soát."""
        session = self._get_session(session_id)

        existing = self._reconciliations.find_open_for_session(session_id)
        if existing is not None:
            return existing

        if not reconciled_by or not reconciled_by.strip():
            raise InvalidIntakeReconciliation(
                "Phải cho biết người thực hiện đối soát (reconciled_by)"
            )

        try:
            reconciliation = IntakeReconciliation(
                id=None,
                session_id=session_id,
                status="OPEN",
                control_totals=dict(session.control_totals or {}),
                findings=[],
                reconciled_by=reconciled_by.strip(),
                opened_at=_utc_now_iso(),
            )
        except ValueError as exc:
            raise InvalidIntakeReconciliation(str(exc)) from exc

        return self._reconciliations.add(reconciliation)

    # ---------- Xem lại phiên đối soát ----------

    def get(self, reconciliation_id: int) -> IntakeReconciliation:
        reconciliation = self._reconciliations.get_by_id(reconciliation_id)
        if reconciliation is None:
            raise IntakeReconciliationNotFound(reconciliation_id)
        return reconciliation

    def list_reconciliations(
        self,
        session_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[IntakeReconciliation]:
        return self._reconciliations.list(session_id=session_id, status=status)

    # ---------- Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu ----------

    def mark_finding(
        self,
        reconciliation_id: int,
        finding_type: str,
        field_name: str,
        description: str,
    ) -> IntakeReconciliation:
        reconciliation = self.get(reconciliation_id)
        try:
            reconciliation.mark_finding(
                finding_type=finding_type,
                field_name=field_name,
                description=description,
                recorded_at=_utc_now_iso(),
            )
        except ValueError as exc:
            message = str(exc)
            if not reconciliation.is_open:
                raise IntakeReconciliationAlreadyClosed(reconciliation_id) from exc
            raise InvalidIntakeReconciliation(message) from exc

        return self._reconciliations.update(reconciliation)

    # ---------- Xử lý xong 1 phát hiện (điều kiện để đóng "đạt yêu cầu") ----------

    def resolve_finding(
        self, reconciliation_id: int, finding_index: int
    ) -> IntakeReconciliation:
        reconciliation = self.get(reconciliation_id)
        try:
            reconciliation.resolve_finding(finding_index, resolved_at=_utc_now_iso())
        except ValueError as exc:
            if finding_index < 0 or finding_index >= len(reconciliation.findings):
                raise IntakeReconciliationFindingNotFound(
                    reconciliation_id, finding_index
                ) from exc
            raise InvalidIntakeReconciliation(str(exc)) from exc

        return self._reconciliations.update(reconciliation)

    # ---------- Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> cập nhật trạng thái ----------

    def close(
        self,
        reconciliation_id: int,
        closed_by: str,
        close_note: str = "",
    ) -> IntakeReconciliation:
        reconciliation = self.get(reconciliation_id)

        if not reconciliation.is_open:
            raise IntakeReconciliationAlreadyClosed(reconciliation_id)

        open_count = reconciliation.open_finding_count()
        if open_count > 0:
            raise IntakeReconciliationHasUnresolvedFindings(reconciliation_id, open_count)

        try:
            reconciliation.close(
                closed_by=closed_by,
                close_note=close_note,
                closed_at=_utc_now_iso(),
            )
        except ValueError as exc:
            raise InvalidIntakeReconciliation(str(exc)) from exc

        return self._reconciliations.update(reconciliation)