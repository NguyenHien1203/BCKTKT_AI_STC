import { dataQualityClient } from "./parsingJobs.js";

// UC-033 (Quản lý danh mục đơn vị) dùng chung data-quality-service nên
// dùng lại `dataQualityClient` (baseURL "/api/data-quality") của
// UC-029/030/031/032 -- không cần proxy dev mới.

export async function getOrgUnitTree({ includeClosed = true } = {}) {
  const { data } = await dataQualityClient.get("/org-unit-catalog/tree", {
    params: { include_closed: includeClosed },
  });
  return data;
}

export async function listOrgUnits({
  parentId = null,
  onlyRoot = false,
  unitType = null,
  status = null,
} = {}) {
  const { data } = await dataQualityClient.get("/org-unit-catalog", {
    params: {
      ...(parentId !== null ? { parent_id: parentId } : {}),
      only_root: onlyRoot,
      ...(unitType ? { unit_type: unitType } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getOrgUnit(id) {
  const { data } = await dataQualityClient.get(`/org-unit-catalog/${id}`);
  return data;
}

export async function listOrgUnitVersions(id) {
  const { data } = await dataQualityClient.get(`/org-unit-catalog/${id}/versions`);
  return data;
}

/** Bước 2 "Thêm đơn vị mới" -- hệ thống kiểm tra trùng mã + lưu phiên bản. */
export async function createOrgUnit({
  code,
  name,
  unitType,
  parentId = null,
  effectiveFrom = null,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/org-unit-catalog", {
    code,
    name,
    unit_type: unitType,
    ...(parentId ? { parent_id: parentId } : {}),
    ...(effectiveFrom ? { effective_from: effectiveFrom } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Sửa thông tin đơn vị" -- hệ thống lưu (tăng version + ghi lịch sử). */
export async function updateOrgUnit(
  id,
  { name = null, unitType = null, parentId = undefined, clearParent = false, note = null },
) {
  const { data } = await dataQualityClient.put(`/org-unit-catalog/${id}`, {
    ...(name ? { name } : {}),
    ...(unitType ? { unit_type: unitType } : {}),
    ...(parentId !== undefined && parentId !== null ? { parent_id: parentId } : {}),
    clear_parent: clearParent,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 4 "Đóng đơn vị" -- hệ thống lưu effective_to. */
export async function closeOrgUnit(id, { effectiveTo, note = null }) {
  const { data } = await dataQualityClient.post(`/org-unit-catalog/${id}/close`, {
    effective_to: effectiveTo,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 4 "Tách đơn vị" -- hệ thống lưu effective_from/to. */
export async function splitOrgUnit(id, { effectiveFrom, newUnits, note = null }) {
  const { data } = await dataQualityClient.post(`/org-unit-catalog/${id}/split`, {
    effective_from: effectiveFrom,
    new_units: newUnits,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 4 "Sáp nhập đơn vị" -- hệ thống lưu effective_from/to. */
export async function mergeOrgUnits({ sourceUnitIds, target, effectiveFrom, note = null }) {
  const { data } = await dataQualityClient.post("/org-unit-catalog/merge", {
    source_unit_ids: sourceUnitIds,
    target,
    effective_from: effectiveFrom,
    ...(note ? { note } : {}),
  });
  return data;
}