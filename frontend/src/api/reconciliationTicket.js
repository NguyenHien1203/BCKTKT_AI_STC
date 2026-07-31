import { ingestionClient } from "./dataSources.js";

// UC-028: Xử lý ticket đối soát với chủ quản nguồn. Dùng chung
// `ingestionClient` (baseURL "/api/ingestion") vì cùng thuộc ingestion-service.

// ---------- Bước 1: Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu + thông báo ----------

export async function openReconciliationTicket({
  reconciliationId,
  sourceOwner,
  title,
  description = "",
  openedBy = "",
}) {
  const { data } = await ingestionClient.post("/reconciliation-tickets", {
    reconciliation_id: reconciliationId,
    source_owner: sourceOwner,
    title,
    description,
    opened_by: openedBy,
  });
  return data;
}

// ---------- Xem lại ticket ----------

export async function listReconciliationTickets({
  reconciliationId = null,
  status = null,
} = {}) {
  const { data } = await ingestionClient.get("/reconciliation-tickets", {
    params: {
      ...(reconciliationId ? { reconciliation_id: reconciliationId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getReconciliationTicket(id) {
  const { data } = await ingestionClient.get(`/reconciliation-tickets/${id}`);
  return data;
}

// ---------- Bước 2: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử ----------

export async function addReconciliationTicketProgress(
  ticketId,
  { note, updatedBy, status = null },
) {
  const { data } = await ingestionClient.post(`/reconciliation-tickets/${ticketId}/progress`, {
    note,
    updated_by: updatedBy,
    ...(status ? { status } : {}),
  });
  return data;
}

// ---------- Bước 3: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký ----------

export async function closeReconciliationTicket(ticketId, { closedBy, closeNote = "" }) {
  const { data } = await ingestionClient.post(`/reconciliation-tickets/${ticketId}/close`, {
    closed_by: closedBy,
    close_note: closeNote,
  });
  return data;
}