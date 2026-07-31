"""Application layer — UC-028: Xử lý ticket đối soát với chủ quản nguồn.

Đối chiếu docs/use_cases.json id=28, actor "Quản trị Tích hợp". Luồng
nghiệp vụ:
1. Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu ticket + thông báo.
2. Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử.
3. Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký.

Không tạo lại hạ tầng "phiên đối soát" — tái sử dụng
`IntakeReconciliationRepository` (UC-027) chỉ để xác nhận `reconciliation_id`
hợp lệ khi mở ticket; mỗi ticket được ghi lại vào `reconciliation_tickets`
(`ReconciliationTicketRepository`) để tra cứu lịch sử xử lý với chủ quản
nguồn.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import ReconciliationTicket
from app.domain.exceptions import (
    IntakeReconciliationNotFound,
    InvalidReconciliationTicket,
    ReconciliationTicketAlreadyClosed,
    ReconciliationTicketNotFound,
    ReconciliationTicketNotResolved,
)
from app.domain.repositories import IntakeReconciliationRepository, ReconciliationTicketRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReconciliationTicketService:
    def __init__(
        self,
        ticket_repo: ReconciliationTicketRepository,
        reconciliation_repo: IntakeReconciliationRepository,
    ):
        self._tickets = ticket_repo
        self._reconciliations = reconciliation_repo

    def _get_reconciliation(self, reconciliation_id: int):
        reconciliation = self._reconciliations.get_by_id(reconciliation_id)
        if reconciliation is None:
            raise IntakeReconciliationNotFound(reconciliation_id)
        return reconciliation

    # ---------- Bước 1: Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu + thông báo ----------

    def open_ticket(
        self,
        reconciliation_id: int,
        source_owner: str,
        title: str,
        description: str,
        opened_by: str,
    ) -> ReconciliationTicket:
        """Mở ticket xử lý với chủ quản nguồn (`source_owner`), gắn với 1
        phiên đối soát đã tồn tại -> hệ thống lưu ticket, đồng thời "thông
        báo" cho chủ quản nguồn (mô phỏng bằng cờ `notified=True`)."""
        self._get_reconciliation(reconciliation_id)

        try:
            ticket = ReconciliationTicket(
                id=None,
                reconciliation_id=reconciliation_id,
                source_owner=source_owner.strip() if source_owner else source_owner,
                title=title.strip() if title else title,
                description=(description or "").strip(),
                status="OPEN",
                history=[],
                opened_by=(opened_by or "").strip(),
                opened_at=_utc_now_iso(),
                notified=True,
            )
        except ValueError as exc:
            raise InvalidReconciliationTicket(str(exc)) from exc

        return self._tickets.add(ticket)

    # ---------- Xem lại ticket ----------

    def get(self, ticket_id: int) -> ReconciliationTicket:
        ticket = self._tickets.get_by_id(ticket_id)
        if ticket is None:
            raise ReconciliationTicketNotFound(ticket_id)
        return ticket

    def list_tickets(
        self,
        reconciliation_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[ReconciliationTicket]:
        return self._tickets.list(reconciliation_id=reconciliation_id, status=status)

    # ---------- Bước 2: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử ----------

    def add_progress(
        self,
        ticket_id: int,
        note: str,
        updated_by: str,
        status: Optional[str] = None,
    ) -> ReconciliationTicket:
        ticket = self.get(ticket_id)
        try:
            ticket.add_progress(
                note=note,
                updated_by=updated_by,
                updated_at=_utc_now_iso(),
                status=status,
            )
        except ValueError as exc:
            if ticket.is_closed:
                raise ReconciliationTicketAlreadyClosed(ticket_id) from exc
            raise InvalidReconciliationTicket(str(exc)) from exc

        return self._tickets.update(ticket)

    # ---------- Bước 3: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký ----------

    def close(
        self,
        ticket_id: int,
        closed_by: str,
        close_note: str = "",
    ) -> ReconciliationTicket:
        ticket = self.get(ticket_id)

        if ticket.is_closed:
            raise ReconciliationTicketAlreadyClosed(ticket_id)
        if not ticket.is_resolved:
            raise ReconciliationTicketNotResolved(ticket_id)

        try:
            ticket.close(
                closed_by=closed_by,
                close_note=close_note,
                closed_at=_utc_now_iso(),
            )
        except ValueError as exc:
            raise InvalidReconciliationTicket(str(exc)) from exc

        return self._tickets.update(ticket)