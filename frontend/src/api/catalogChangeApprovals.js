import { dataQualityClient } from "./parsingJobs.js";

// UC-037 (Phê duyệt thay đổi danh mục nhạy cảm) dùng chung
// data-quality-service với UC-036 nên dùng lại `dataQualityClient`
// (baseURL "/api/data-quality") -- không cần proxy dev mới.

/** Bước 1 "Xem các yêu cầu chờ duyệt" -- hệ thống hiển thị. */
export async function listPendingChangeRequests({ catalogType = null } = {}) {
  const { data } = await dataQualityClient.get("/catalog-change-approvals/pending", {
    params: { ...(catalogType ? { catalog_type: catalogType } : {}) },
  });
  return data;
}

/** Bước 2 "Hệ thống hiển thị diff". */
export async function getChangeRequestDiff(requestId) {
  const { data } = await dataQualityClient.get(
    `/catalog-change-approvals/${requestId}/diff`,
  );
  return data;
}

/** Bước 3 "Phê duyệt" + bước 4 "Hệ thống cập nhật và áp dụng thay đổi" +

 * bước 5 "Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký" (reason bắt buộc). */
export async function approveChangeRequest(requestId, { decidedBy, reason }) {
  const { data } = await dataQualityClient.post(
    `/catalog-change-approvals/${requestId}/approve`,
    { decided_by: decidedBy, reason },
  );
  return data;
}

/** Bước 3 "Từ chối" (không áp dụng thay đổi) + bước 5 "Ghi lý do -- nhật ký". */
export async function rejectChangeRequest(requestId, { decidedBy, reason }) {
  const { data } = await dataQualityClient.post(
    `/catalog-change-approvals/${requestId}/reject`,
    { decided_by: decidedBy, reason },
  );
  return data;
}

/** Bước 5 "Hệ thống lưu vào nhật ký" -- tra cứu lại nhật ký phê duyệt. */
export async function listChangeApprovalAuditLogs({
  requestId = null,
  entryId = null,
  catalogType = null,
  action = null,
} = {}) {
  const { data } = await dataQualityClient.get("/catalog-change-approvals/audit-logs", {
    params: {
      ...(requestId ? { request_id: requestId } : {}),
      ...(entryId ? { entry_id: entryId } : {}),
      ...(catalogType ? { catalog_type: catalogType } : {}),
      ...(action ? { action } : {}),
    },
  });
  return data;
}