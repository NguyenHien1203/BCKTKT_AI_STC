import axios from "axios";

// Qua Vite dev proxy (xem vite.config.js) -> api-gateway-service (port 8005).
// Khi build production, đổi baseURL này thành URL của APISIX Gateway thật.
export const apiGatewayClient = axios.create({
  baseURL: "/api/api-gateway",
});

export const API_CATALOG_TYPES = ["SEARCH", "QA", "DATA", "METADATA"];

// ---------- UC-058: Quản lý danh mục API ----------

// Bước 1 — Publish API mới.
export async function publishApiCatalogEntry(payload) {
  const { data } = await apiGatewayClient.post("/api-catalog", payload);
  return data;
}

export async function listApiCatalog({ apiType = null, status = null } = {}) {
  const { data } = await apiGatewayClient.get("/api-catalog", {
    params: {
      ...(apiType ? { api_type: apiType } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getApiCatalogEntry(id) {
  const { data } = await apiGatewayClient.get(`/api-catalog/${id}`);
  return data;
}

export async function listApiCatalogVersions(id) {
  const { data } = await apiGatewayClient.get(`/api-catalog/${id}/versions`);
  return data;
}

// Bước 2 — Gỡ công bố API (vô hiệu hoá điểm cuối).
export async function unpublishApiCatalogEntry(id) {
  const { data } = await apiGatewayClient.post(`/api-catalog/${id}/unpublish`);
  return data;
}

export async function republishApiCatalogEntry(id) {
  const { data } = await apiGatewayClient.post(`/api-catalog/${id}/republish`);
  return data;
}

// Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ.
export async function configureApiCatalogVersion(id, payload) {
  const { data } = await apiGatewayClient.put(`/api-catalog/${id}/version`, payload);
  return data;
}