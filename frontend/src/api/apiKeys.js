import { apiGatewayClient } from "./apiCatalog.js";

// Dùng chung `apiGatewayClient` (đã trỏ tới api-gateway-service qua proxy
// `/api/api-gateway`, xem vite.config.js) — cùng service đã phục vụ UC-058.

// ---------- UC-059: Quản lý API key ----------

// Bước 1 — Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá + phạm vi.
// Response kèm `raw_key` — CHỈ hiển thị 1 LẦN DUY NHẤT, không lấy lại được.
export async function createApiKey(payload) {
  const { data } = await apiGatewayClient.post("/api-keys", payload);
  return data;
}

export async function listApiKeys({ consumerCode = null, status = null } = {}) {
  const { data } = await apiGatewayClient.get("/api-keys", {
    params: {
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getApiKey(id) {
  const { data } = await apiGatewayClient.get(`/api-keys/${id}`);
  return data;
}

// Bước 2 — Thu hồi khoá API -> hệ thống thu hồi.
export async function revokeApiKey(id) {
  const { data } = await apiGatewayClient.post(`/api-keys/${id}/revoke`);
  return data;
}

// Bước 3 — Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo khoá
// mới + thời gian ân hạn. Response `new_key.raw_key` CHỈ hiển thị 1 lần.
export async function rotateApiKey(id, { gracePeriodDays = null, rotationMode = "MANUAL" } = {}) {
  const { data } = await apiGatewayClient.post(`/api-keys/${id}/rotate`, {
    grace_period_days: gracePeriodDays,
    rotation_mode: rotationMode,
  });
  return data;
}

// Bước 4 — Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký.
export async function logApiKeyUsage(id, payload) {
  const { data } = await apiGatewayClient.post(`/api-keys/${id}/usage-logs`, payload);
  return data;
}

export async function listApiKeyUsageLogs(id, limit = 100) {
  const { data } = await apiGatewayClient.get(`/api-keys/${id}/usage-logs`, {
    params: { limit },
  });
  return data;
}