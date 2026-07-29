import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Bước 1: Định nghĩa tập dữ liệu + lược đồ ----------

export async function listDatasets({ dataSourceId = null, onlyActive = false } = {}) {
  const { data } = await ingestionClient.get("/datasets", {
    params: {
      only_active: onlyActive,
      ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
    },
  });
  return data;
}

export async function getDataset(id) {
  const { data } = await ingestionClient.get(`/datasets/${id}`);
  return data;
}

export async function defineDataset(payload) {
  const { data } = await ingestionClient.post("/datasets", payload);
  return data;
}

export async function updateDatasetSchema(id, schemaFields) {
  const { data } = await ingestionClient.put(`/datasets/${id}/schema`, {
    schema_fields: schemaFields,
  });
  return data;
}

export async function deactivateDataset(id) {
  const { data } = await ingestionClient.post(`/datasets/${id}/deactivate`);
  return data;
}

export async function activateDataset(id) {
  const { data } = await ingestionClient.post(`/datasets/${id}/activate`);
  return data;
}

// ---------- Bước 2: Khoá chính + chiến lược phân mảnh ----------

export async function configurePartitioning(id, { primaryKey, partitionStrategy, partitionColumn }) {
  const { data } = await ingestionClient.post(`/datasets/${id}/partitioning`, {
    primary_key: primaryKey,
    partition_strategy: partitionStrategy,
    partition_column: partitionColumn || null,
  });
  return data;
}

// ---------- Bước 3: Trường bắt buộc (NOT NULL) ----------

export async function listCriticalFields(id) {
  const { data } = await ingestionClient.get(`/datasets/${id}/critical-fields`);
  return data;
}

export async function declareCriticalFields(id, fieldNames) {
  const { data } = await ingestionClient.post(`/datasets/${id}/critical-fields`, {
    field_names: fieldNames,
  });
  return data;
}

// ---------- Bước 4: Đăng ký Schema Registry ----------

export async function registerSchemaVersion(id) {
  const { data } = await ingestionClient.post(`/datasets/${id}/schema-versions`);
  return data;
}

export async function listSchemaVersions(id) {
  const { data } = await ingestionClient.get(`/datasets/${id}/schema-versions`);
  return data;
}

export async function getSchemaVersion(id, version) {
  const { data } = await ingestionClient.get(`/datasets/${id}/schema-versions/${version}`);
  return data;
}