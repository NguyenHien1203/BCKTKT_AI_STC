import { apiGatewayClient } from "./apiCatalog.js";

// Dùng chung `apiGatewayClient` (đã trỏ tới api-gateway-service qua proxy
// `/api/api-gateway`, xem vite.config.js) — cùng service đã phục vụ
// UC-058/UC-059.

export const SERVICE_TIER_CODES = ["FREE", "STANDARD", "PREMIUM"];
export const THROTTLE_POLICIES = ["REJECT", "QUEUE", "DELAY"];

// ---------- UC-060: Quản lý giới hạn tần suất + gói dịch vụ ----------

// Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
export async function createServiceTier(payload) {
  const { data } = await apiGatewayClient.post("/service-tiers", payload);
  return data;
}

export async function listServiceTiers({ isActive = null } = {}) {
  const { data } = await apiGatewayClient.get("/service-tiers", {
    params: {
      ...(isActive === null ? {} : { is_active: isActive }),
    },
  });
  return data;
}

export async function getServiceTier(id) {
  const { data } = await apiGatewayClient.get(`/service-tiers/${id}`);
  return data;
}

export async function updateServiceTier(id, payload) {
  const { data } = await apiGatewayClient.put(`/service-tiers/${id}`, payload);
  return data;
}

// Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) -> hệ
// thống áp dụng tại Cổng API.
export async function configureRateLimit(tierId, { requestsPerSecond, requestsPerDay }) {
  const { data } = await apiGatewayClient.put(`/service-tiers/${tierId}/rate-limit`, {
    requests_per_second: requestsPerSecond,
    requests_per_day: requestsPerDay,
  });
  return data;
}

export async function getRateLimit(tierId) {
  const { data } = await apiGatewayClient.get(`/service-tiers/${tierId}/rate-limit`);
  return data;
}

// Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ thống
// lưu.
export async function configureBurstPolicy(
  tierId,
  { burstLimit, windowSeconds, throttlePolicy }
) {
  const { data } = await apiGatewayClient.put(`/service-tiers/${tierId}/burst-policy`, {
    burst_limit: burstLimit,
    window_seconds: windowSeconds,
    throttle_policy: throttlePolicy,
  });
  return data;
}

export async function getBurstPolicy(tierId) {
  const { data } = await apiGatewayClient.get(`/service-tiers/${tierId}/burst-policy`);
  return data;
}