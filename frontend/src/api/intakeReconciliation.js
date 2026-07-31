import { ingestionClient } from "./dataSources.js";

// UC-027: Đối soát phiên intake. Dùng chung `ingestionClient`
// (baseURL "/api/ingestion") vì cùng thuộc ingestion-service.

// ---------- Bước 1-2: Chọn phiên cần đối soát -> hệ thống hiển thị tổng kiểm soát ----------

export async function openIntakeReconciliation({ sessionId, reconciledBy }) {
  const { data } = await ingestionClient.post("/intake-reconciliations", {
    session_id: sessionId,
    reconciled_by: reconciledBy,
  });
  return data;
}

// ---------- Xem lại phiên đối soát ----------

export async function listIntakeReconciliations({ sessionId = null, status = null } = {}) {
  const { data } = await ingestionClient.get("/intake-reconciliations", {
    params: {
      ...(sessionId ? { session_id: sessionId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getIntakeReconciliation(id) {
  const { data } = await ingestionClient.get(`/intake-reconciliations/${id}`);
  return data;
}

// ---------- Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu ----------

export async function markIntakeReconciliationFinding(
  reconciliationId,
  { findingType, fieldName, description },
) {
  const { data } = await ingestionClient.post(
    `/intake-reconciliations/${reconciliationId}/findings`,
    {
      finding_type: findingType,
      field_name: fieldName,
      description,
    },
  );
  return data;
}

// ---------- Xử lý xong 1 phát hiện (điều kiện để đóng phiên "đạt yêu cầu") ----------

export async function resolveIntakeReconciliationFinding(reconciliationId, findingIndex) {
  const { data } = await ingestionClient.post(
    `/intake-reconciliations/${reconciliationId}/findings/${findingIndex}/resolve`,
  );
  return data;
}

// ---------- Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> hệ thống cập nhật trạng thái ----------

export async function closeIntakeReconciliation(reconciliationId, { closedBy, closeNote = "" }) {
  const { data } = await ingestionClient.post(
    `/intake-reconciliations/${reconciliationId}/close`,
    {
      closed_by: closedBy,
      close_note: closeNote,
    },
  );
  return data;
}