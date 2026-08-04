import { dataQualityClient } from "./parsingJobs.js";

// UC-036 (Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn) dùng chung
// data-quality-service nên dùng lại `dataQualityClient` (baseURL
// "/api/data-quality") của UC-029/.../035 — không cần proxy dev mới.

export const CATALOG_TYPES = ["ITEM", "DOCUMENT_TYPE", "FUNDING_SOURCE"];

/** Bước 1 "Xem từng danh mục (mặt hàng / loại văn bản / nguồn vốn)" -- hệ thống hiển thị. */
export async function listCatalogEntries({ catalogType = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/catalog-entries", {
    params: {
      ...(catalogType ? { catalog_type: catalogType } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getCatalogEntry(id) {
  const { data } = await dataQualityClient.get(`/catalog-entries/${id}`);
  return data;
}

export async function listCatalogEntryVersions(id) {
  const { data } = await dataQualityClient.get(`/catalog-entries/${id}/versions`);
  return data;
}

/** Bước 2 "Thêm entry" -- hệ thống quản lý phiên bản. */
export async function createCatalogEntry({
  catalogType,
  code,
  name,
  unit = null,
  description = null,
  isSensitive = false,
  effectiveFrom = null,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/catalog-entries", {
    catalog_type: catalogType,
    code,
    name,
    ...(unit ? { unit } : {}),
    ...(description ? { description } : {}),
    is_sensitive: isSensitive,
    ...(effectiveFrom ? { effective_from: effectiveFrom } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 2 "Sửa entry" -- hệ thống quản lý phiên bản (tăng version + ghi lịch sử).

 * Trả lỗi 409 CATALOG_ENTRY_SENSITIVE_REQUIRES_APPROVAL nếu mục là mục nhạy
 * cảm -- dùng `proposeCatalogEntryChange` (bước 3) thay thế. */
export async function updateCatalogEntry(
  id,
  { name = null, unit = null, description = null, status = null, note = null },
) {
  const { data } = await dataQualityClient.put(`/catalog-entries/${id}`, {
    ...(name ? { name } : {}),
    ...(unit !== null ? { unit } : {}),
    ...(description !== null ? { description } : {}),
    ...(status ? { status } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Đề nghị thay đổi danh mục nhạy cảm" -- hệ thống lưu yêu cầu chờ duyệt. */
export async function proposeCatalogEntryChange(
  entryId,
  {
    requestedBy,
    reason,
    proposedName = null,
    proposedUnit = null,
    proposedDescription = null,
    proposedStatus = null,
    proposedIsSensitive = null,
  },
) {
  const { data } = await dataQualityClient.post(
    `/catalog-entries/${entryId}/change-requests`,
    {
      requested_by: requestedBy,
      reason,
      ...(proposedName !== null ? { proposed_name: proposedName } : {}),
      ...(proposedUnit !== null ? { proposed_unit: proposedUnit } : {}),
      ...(proposedDescription !== null ? { proposed_description: proposedDescription } : {}),
      ...(proposedStatus !== null ? { proposed_status: proposedStatus } : {}),
      ...(proposedIsSensitive !== null ? { proposed_is_sensitive: proposedIsSensitive } : {}),
    },
  );
  return data;
}

export async function listCatalogChangeRequests({
  entryId = null,
  catalogType = null,
  status = null,
} = {}) {
  const { data } = await dataQualityClient.get("/catalog-entries/change-requests/list", {
    params: {
      ...(entryId ? { entry_id: entryId } : {}),
      ...(catalogType ? { catalog_type: catalogType } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getCatalogChangeRequest(id) {
  const { data } = await dataQualityClient.get(`/catalog-entries/change-requests/${id}`);
  return data;
}

/** Duyệt yêu cầu thay đổi -- áp dụng vào mục danh mục (dùng bởi UC-037). */
export async function approveCatalogChangeRequest(id, { reviewedBy, reviewNote = null }) {
  const { data } = await dataQualityClient.post(
    `/catalog-entries/change-requests/${id}/approve`,
    { reviewed_by: reviewedBy, ...(reviewNote ? { review_note: reviewNote } : {}) },
  );
  return data;
}

export async function rejectCatalogChangeRequest(id, { reviewedBy, reviewNote = null }) {
  const { data } = await dataQualityClient.post(
    `/catalog-entries/change-requests/${id}/reject`,
    { reviewed_by: reviewedBy, ...(reviewNote ? { review_note: reviewNote } : {}) },
  );
  return data;
}