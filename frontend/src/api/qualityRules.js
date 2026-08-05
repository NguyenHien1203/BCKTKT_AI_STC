import { dataQualityClient } from "./parsingJobs.js";

// UC-038 (Quản lý quy tắc kiểm tra chất lượng) dùng chung
// data-quality-service với UC-029/.../037 nên dùng lại `dataQualityClient`
// (baseURL "/api/data-quality") -- không cần proxy dev mới.

export const QUALITY_RULE_TYPES = [
  { value: "COMPLETENESS", label: "Đầy đủ" },
  { value: "VALIDITY", label: "Hợp lệ" },
  { value: "UNIQUENESS", label: "Duy nhất" },
  { value: "CONSISTENCY", label: "Nhất quán" },
];

/** Bước 1 "Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ / duy nhất / nhất quán)". */
export async function listQualityRules({ datasetId = null, ruleType = null, isActive = null } = {}) {
  const { data } = await dataQualityClient.get("/quality-rules", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(ruleType ? { rule_type: ruleType } : {}),
      ...(isActive !== null ? { is_active: isActive } : {}),
    },
  });
  return data;
}

export async function getQualityRule(id) {
  const { data } = await dataQualityClient.get(`/quality-rules/${id}`);
  return data;
}

export async function listQualityRuleVersions(id) {
  const { data } = await dataQualityClient.get(`/quality-rules/${id}/versions`);
  return data;
}

/** Bước 2 "Thêm quy tắc" -- hệ thống lưu vào metadata.quality_rules + version. */
export async function createQualityRule({
  fieldNames,
  ruleType,
  datasetId = null,
  params = {},
  weight = 1.0,
  description = null,
  isActive = true,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/quality-rules", {
    field_names: fieldNames,
    rule_type: ruleType,
    dataset_id: datasetId,
    params,
    weight,
    ...(description ? { description } : {}),
    is_active: isActive,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 2 "Sửa quy tắc" -- hệ thống lưu vào metadata.quality_rules + version (tăng version). */
export async function updateQualityRule(
  id,
  { fieldNames = null, params = null, weight = null, description = null, isActive = null, note = null },
) {
  const { data } = await dataQualityClient.put(`/quality-rules/${id}`, {
    ...(fieldNames !== null ? { field_names: fieldNames } : {}),
    ...(params !== null ? { params } : {}),
    ...(weight !== null ? { weight } : {}),
    ...(description !== null ? { description } : {}),
    ...(isActive !== null ? { is_active: isActive } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Cấu hình ngưỡng + trọng số cho điểm" -- hệ thống lưu. */
export async function saveQualityScoreConfig({
  datasetId = null,
  passThreshold,
  ruleTypeWeights = {},
  note = null,
}) {
  const { data } = await dataQualityClient.put("/quality-rules/score-configs", {
    dataset_id: datasetId,
    pass_threshold: passThreshold,
    rule_type_weights: ruleTypeWeights,
    ...(note ? { note } : {}),
  });
  return data;
}

export async function getQualityScoreConfigByDataset(datasetId = null) {
  const { data } = await dataQualityClient.get("/quality-rules/score-configs/by-dataset", {
    params: { ...(datasetId !== null ? { dataset_id: datasetId } : {}) },
  });
  return data;
}

export async function listQualityScoreConfigs() {
  const { data } = await dataQualityClient.get("/quality-rules/score-configs/list");
  return data;
}

export async function listQualityScoreConfigVersions(configId) {
  const { data } = await dataQualityClient.get(`/quality-rules/score-configs/${configId}/versions`);
  return data;
}