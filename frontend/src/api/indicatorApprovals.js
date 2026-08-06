import { dataQualityClient } from "./parsingJobs.js";

// UC-044 (Phê duyệt chỉ tiêu) dùng chung data-quality-service với
// UC-029/.../043 nên dùng lại `dataQualityClient` (baseURL
// "/api/data-quality") -- không cần proxy dev mới.

/** Tiền đề: Quản trị Dữ liệu gửi 1 chỉ tiêu đang DRAFT để chờ duyệt. */
export async function submitIndicatorForApproval(indicatorId, { submittedBy = null, note = null } = {}) {
  const { data } = await dataQualityClient.post(`/indicator-approvals/${indicatorId}/submit`, {
    ...(submittedBy ? { submitted_by: submittedBy } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 1 "Xem chỉ tiêu chờ phê duyệt" -- hệ thống hiển thị. */
export async function listPendingIndicatorApprovals({ domain = null } = {}) {
  const { data } = await dataQualityClient.get("/indicator-approvals/pending", {
    params: { ...(domain ? { domain } : {}) },
  });
  return data;
}

/** Bước 2 "Xem kết quả kiểm thử + so sánh với số liệu hiện tại". */
export async function getIndicatorComparison(indicatorId) {
  const { data } = await dataQualityClient.get(`/indicator-approvals/${indicatorId}/comparison`);
  return data;
}

/** Bước 3 "Phê duyệt chỉ tiêu" -- hệ thống công bố (status=ACTIVE). */
export async function approveIndicator(indicatorId, { decidedBy = null, reason, note = null }) {
  const { data } = await dataQualityClient.post(`/indicator-approvals/${indicatorId}/approve`, {
    ...(decidedBy ? { decided_by: decidedBy } : {}),
    reason,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Từ chối chỉ tiêu" -- hệ thống trả về cho Quản trị Dữ liệu (status=DRAFT). */
export async function rejectIndicator(indicatorId, { decidedBy = null, reason, note = null }) {
  const { data } = await dataQualityClient.post(`/indicator-approvals/${indicatorId}/reject`, {
    ...(decidedBy ? { decided_by: decidedBy } : {}),
    reason,
    ...(note ? { note } : {}),
  });
  return data;
}

export async function listIndicatorApprovalDecisions(indicatorId) {
  const { data } = await dataQualityClient.get(`/indicator-approvals/${indicatorId}/decisions`);
  return data;
}