import { dataQualityClient } from "./parsingJobs.js";

// UC-031 (Ánh xạ trường sang dạng chuẩn) dùng chung data-quality-service
// nên dùng lại `dataQualityClient` (baseURL "/api/data-quality") của UC-029.

export async function createMappingRule({
  fieldName,
  version = 1,
  ruleType,
  datasetId = null,
  catalogMap = {},
  normalizeCase = null,
  isActive = true,
}) {
  const { data } = await dataQualityClient.post("/mapping-rules", {
    field_name: fieldName,
    version,
    rule_type: ruleType,
    ...(datasetId ? { dataset_id: datasetId } : {}),
    catalog_map: catalogMap,
    ...(normalizeCase ? { normalize_case: normalizeCase } : {}),
    is_active: isActive,
  });
  return data;
}

export async function listMappingRules({ datasetId = null, fieldName = null, isActive = null } = {}) {
  const { data } = await dataQualityClient.get("/mapping-rules", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(fieldName ? { field_name: fieldName } : {}),
      ...(isActive !== null ? { is_active: isActive } : {}),
    },
  });
  return data;
}

export async function receiveMappingRequested({ parsingJobId, datasetId = null }) {
  const { data } = await dataQualityClient.post("/mapping-jobs", {
    parsing_job_id: parsingJobId,
    ...(datasetId ? { dataset_id: datasetId } : {}),
  });
  return data;
}

export async function listMappingJobs({ datasetId = null, parsingJobId = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/mapping-jobs", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(parsingJobId ? { parsing_job_id: parsingJobId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getMappingJob(id) {
  const { data } = await dataQualityClient.get(`/mapping-jobs/${id}`);
  return data;
}

export async function listMappingRejections(id) {
  const { data } = await dataQualityClient.get(`/mapping-jobs/${id}/rejections`);
  return data;
}

export async function listUnmappedQueue(id) {
  const { data } = await dataQualityClient.get(`/mapping-jobs/${id}/unmapped-queue`);
  return data;
}

export async function listMappedStandardRecords(id) {
  const { data } = await dataQualityClient.get(`/mapping-jobs/${id}/standard-records`);
  return data;
}