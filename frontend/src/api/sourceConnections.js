import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Cấu hình + kiểm thử kết nối (source-connections) ----------

export async function listSourceConnections({
  dataSourceId = null,
  connectionType = null,
  onlyActive = false,
} = {}) {
  const { data } = await ingestionClient.get("/source-connections", {
    params: {
      only_active: onlyActive,
      ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
      ...(connectionType ? { connection_type: connectionType } : {}),
    },
  });
  return data;
}

export async function getSourceConnection(id) {
  const { data } = await ingestionClient.get(`/source-connections/${id}`);
  return data;
}

export async function configureSourceConnection(payload) {
  const { data } = await ingestionClient.post("/source-connections", payload);
  return data;
}

export async function updateSourceConnection(id, payload) {
  const { data } = await ingestionClient.patch(`/source-connections/${id}`, payload);
  return data;
}

export async function testSourceConnection(id) {
  const { data } = await ingestionClient.post(`/source-connections/${id}/test`);
  return data;
}

export async function deactivateSourceConnection(id) {
  const { data } = await ingestionClient.post(`/source-connections/${id}/deactivate`);
  return data;
}

export async function activateSourceConnection(id) {
  const { data } = await ingestionClient.post(`/source-connections/${id}/activate`);
  return data;
}

// ---------- Certificate/API key + lịch luân chuyển + cảnh báo hết hạn ----------

export async function listCredentialAssets({
  connectionId = null,
  assetType = null,
  onlyActive = false,
} = {}) {
  const { data } = await ingestionClient.get("/credential-assets", {
    params: {
      only_active: onlyActive,
      ...(connectionId ? { connection_id: connectionId } : {}),
      ...(assetType ? { asset_type: assetType } : {}),
    },
  });
  return data;
}

export async function registerCredentialAsset(payload) {
  const { data } = await ingestionClient.post("/credential-assets", payload);
  return data;
}

export async function rotateCredentialAsset(id, payload) {
  const { data } = await ingestionClient.post(`/credential-assets/${id}/rotate`, payload);
  return data;
}

export async function deactivateCredentialAsset(id) {
  const { data } = await ingestionClient.post(`/credential-assets/${id}/deactivate`);
  return data;
}

export async function activateCredentialAsset(id) {
  const { data } = await ingestionClient.post(`/credential-assets/${id}/activate`);
  return data;
}

export async function checkExpiringCredentials(daysAhead = 30) {
  const { data } = await ingestionClient.post("/credential-assets/check-expiring", null, {
    params: { days_ahead: daysAhead },
  });
  return data;
}