import axios from "axios";

// Qua Vite dev proxy (xem vite.config.js) -> ingestion-service (port 8002).
// Khi build production, đổi baseURL này thành URL của APISIX Gateway thật.
export const ingestionClient = axios.create({
  baseURL: "/api/ingestion",
});

export async function listDataSources({ onlyActive = false, sourceSystem = null } = {}) {
  const { data } = await ingestionClient.get("/data-sources", {
    params: {
      only_active: onlyActive,
      ...(sourceSystem ? { source_system: sourceSystem } : {}),
    },
  });
  return data;
}

export async function getDataSource(id) {
  const { data } = await ingestionClient.get(`/data-sources/${id}`);
  return data;
}

export async function registerDataSource(payload) {
  const { data } = await ingestionClient.post("/data-sources", payload);
  return data;
}

export async function updateDataSource(id, payload) {
  const { data } = await ingestionClient.patch(`/data-sources/${id}`, payload);
  return data;
}

export async function deactivateDataSource(id) {
  const { data } = await ingestionClient.post(`/data-sources/${id}/deactivate`);
  return data;
}

export async function activateDataSource(id) {
  const { data } = await ingestionClient.post(`/data-sources/${id}/activate`);
  return data;
}