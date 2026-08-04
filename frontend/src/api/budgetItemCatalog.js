import { dataQualityClient } from "./parsingJobs.js";

// UC-034 (Quản lý danh mục khoản mục NSNN) dùng chung data-quality-service
// nên dùng lại `dataQualityClient` (baseURL "/api/data-quality") của
// UC-029/030/031/032/033 -- không cần proxy dev mới.

/** Bước 1 "Xem cây khoản mục NSNN" -- hệ thống hiển thị. */
export async function getBudgetItemTree({ budgetYear, includeClosed = true }) {
  const { data } = await dataQualityClient.get("/budget-item-catalog/tree", {
    params: { budget_year: budgetYear, include_closed: includeClosed },
  });
  return data;
}

export async function listBudgetItems({
  budgetYear = null,
  parentId = null,
  onlyRoot = false,
  level = null,
  status = null,
} = {}) {
  const { data } = await dataQualityClient.get("/budget-item-catalog", {
    params: {
      ...(budgetYear ? { budget_year: budgetYear } : {}),
      ...(parentId !== null ? { parent_id: parentId } : {}),
      only_root: onlyRoot,
      ...(level ? { level } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getBudgetItem(id) {
  const { data } = await dataQualityClient.get(`/budget-item-catalog/${id}`);
  return data;
}

export async function listBudgetItemVersions(id) {
  const { data } = await dataQualityClient.get(`/budget-item-catalog/${id}/versions`);
  return data;
}

/** Bước 2 "Thêm entry" -- hệ thống quản lý phiên bản theo năm ngân sách. */
export async function createBudgetItem({
  code,
  name,
  level,
  budgetYear,
  parentId = null,
  isSensitive = false,
  effectiveFrom = null,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/budget-item-catalog", {
    code,
    name,
    level,
    budget_year: budgetYear,
    ...(parentId ? { parent_id: parentId } : {}),
    is_sensitive: isSensitive,
    ...(effectiveFrom ? { effective_from: effectiveFrom } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 2 "Sửa entry" -- hệ thống quản lý phiên bản theo năm ngân sách.

 * Trả lỗi 409 nếu khoản mục là khoản mục nhạy cảm -- dùng
 * `proposeBudgetItemChange` (bước 3) thay thế. */
export async function updateBudgetItem(id, { name = null, status = null, note = null }) {
  const { data } = await dataQualityClient.put(`/budget-item-catalog/${id}`, {
    ...(name ? { name } : {}),
    ...(status ? { status } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Đề nghị thay đổi khoản mục nhạy cảm" -- hệ thống lưu yêu cầu chờ duyệt. */
export async function proposeBudgetItemChange(
  itemId,
  { requestedBy, reason, proposedName = null, proposedStatus = null, proposedIsSensitive = null },
) {
  const { data } = await dataQualityClient.post(
    `/budget-item-catalog/${itemId}/change-requests`,
    {
      requested_by: requestedBy,
      reason,
      ...(proposedName !== null ? { proposed_name: proposedName } : {}),
      ...(proposedStatus !== null ? { proposed_status: proposedStatus } : {}),
      ...(proposedIsSensitive !== null ? { proposed_is_sensitive: proposedIsSensitive } : {}),
    },
  );
  return data;
}

export async function listBudgetItemChangeRequests({ itemId = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/budget-item-catalog/change-requests/list", {
    params: {
      ...(itemId ? { item_id: itemId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getBudgetItemChangeRequest(id) {
  const { data } = await dataQualityClient.get(`/budget-item-catalog/change-requests/${id}`);
  return data;
}

/** Duyệt yêu cầu -- áp dụng thay đổi vào khoản mục (tăng version + ghi lịch sử). */
export async function approveBudgetItemChange(id, { reviewedBy, reviewNote = null }) {
  const { data } = await dataQualityClient.post(
    `/budget-item-catalog/change-requests/${id}/approve`,
    { reviewed_by: reviewedBy, ...(reviewNote ? { review_note: reviewNote } : {}) },
  );
  return data;
}

export async function rejectBudgetItemChange(id, { reviewedBy, reviewNote = null }) {
  const { data } = await dataQualityClient.post(
    `/budget-item-catalog/change-requests/${id}/reject`,
    { reviewed_by: reviewedBy, ...(reviewNote ? { review_note: reviewNote } : {}) },
  );
  return data;
}