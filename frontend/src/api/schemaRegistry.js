import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Bước 1-3: kiểm tra lược đồ nguồn so với lược đồ đã đăng ký ----------

export async function checkSchemaRegistry(datasetId, { schemaFields, ingestionRunId = null }) {
  const { data } = await ingestionClient.post(`/schema-registry/${datasetId}/check`, {
    schema_fields: schemaFields,
    ingestion_run_id: ingestionRunId,
  });
  return data;
}

// ---------- Xem lịch sử kiểm tra ----------

export async function listSchemaRegistryChecks(datasetId, { status = null } = {}) {
  const { data } = await ingestionClient.get(`/schema-registry/${datasetId}/checks`, {
    params: { ...(status ? { status } : {}) },
  });
  return data;
}

export async function getSchemaRegistryCheck(checkId) {
  const { data } = await ingestionClient.get(`/schema-registry/checks/${checkId}`);
  return data;
}