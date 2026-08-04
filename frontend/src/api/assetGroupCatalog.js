import { dataQualityClient } from "./parsingJobs.js";

// UC-035 (Quản lý danh mục nhóm tài sản) dùng chung data-quality-service
// nên dùng lại `dataQualityClient` (baseURL "/api/data-quality") của
// UC-029/.../034 — không cần proxy dev mới.

/** Bước 1 "Xem danh mục nhóm tài sản (TT 48 / TT 162)" -- hệ thống hiển thị. */
export async function listAssetGroups({ regulation = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/asset-group-catalog", {
    params: {
      ...(regulation ? { regulation } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getAssetGroup(id) {
  const { data } = await dataQualityClient.get(`/asset-group-catalog/${id}`);
  return data;
}

export async function listAssetGroupVersions(id) {
  const { data } = await dataQualityClient.get(`/asset-group-catalog/${id}/versions`);
  return data;
}

/** Bước 2 "Thêm entry" -- hệ thống quản lý phiên bản. */
export async function createAssetGroup({
  code,
  name,
  regulation,
  usefulLifeYears = null,
  effectiveFrom = null,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/asset-group-catalog", {
    code,
    name,
    regulation,
    ...(usefulLifeYears !== null ? { useful_life_years: usefulLifeYears } : {}),
    ...(effectiveFrom ? { effective_from: effectiveFrom } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 2 "Sửa entry" -- hệ thống quản lý phiên bản (tăng version + ghi lịch sử). */
export async function updateAssetGroup(
  id,
  {
    name = null,
    regulation = null,
    usefulLifeYears = null,
    clearUsefulLifeYears = false,
    status = null,
    note = null,
  },
) {
  const { data } = await dataQualityClient.put(`/asset-group-catalog/${id}`, {
    ...(name ? { name } : {}),
    ...(regulation ? { regulation } : {}),
    ...(usefulLifeYears !== null ? { useful_life_years: usefulLifeYears } : {}),
    clear_useful_life_years: clearUsefulLifeYears,
    ...(status ? { status } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Khai báo tỉ lệ khấu hao theo nhóm" -- hệ thống lưu. */
export async function declareAssetDepreciationRate(
  groupId,
  {
    depreciationRatePercent,
    usefulLifeYears = null,
    effectiveFrom = null,
    effectiveTo = null,
    note = null,
    declaredBy = null,
  },
) {
  const { data } = await dataQualityClient.post(
    `/asset-group-catalog/${groupId}/depreciation-rates`,
    {
      depreciation_rate_percent: depreciationRatePercent,
      ...(usefulLifeYears !== null ? { useful_life_years: usefulLifeYears } : {}),
      ...(effectiveFrom ? { effective_from: effectiveFrom } : {}),
      ...(effectiveTo ? { effective_to: effectiveTo } : {}),
      ...(note ? { note } : {}),
      ...(declaredBy ? { declared_by: declaredBy } : {}),
    },
  );
  return data;
}

export async function listAssetDepreciationRates(groupId) {
  const { data } = await dataQualityClient.get(
    `/asset-group-catalog/${groupId}/depreciation-rates`,
  );
  return data;
}

export async function getCurrentAssetDepreciationRate(groupId) {
  const { data } = await dataQualityClient.get(
    `/asset-group-catalog/${groupId}/depreciation-rates/current`,
  );
  return data;
}