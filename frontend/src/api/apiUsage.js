import { apiGatewayClient } from "./apiCatalog.js";

// Dùng chung `apiGatewayClient` (đã trỏ tới api-gateway-service qua proxy
// `/api/api-gateway`, xem vite.config.js) — cùng service đã phục vụ
// UC-058/UC-059/UC-060.

export const ALERT_SEVERITIES = ["INFO", "WARNING", "CRITICAL"];
export const ALERT_STATUSES = ["FIRING", "RESOLVED"];

// ---------- UC-061: Theo dõi mức sử dụng API + chỉ số ----------

// Bước 1 — Xem bảng điều khiển mức sử dụng API -> hệ thống hiển thị từ
// Prometheus.
export async function getApiUsageDashboard({ windowMinutes = 60, stepMinutes = 5 } = {}) {
  const { data } = await apiGatewayClient.get("/api-usage/dashboard", {
    params: { window_minutes: windowMinutes, step_minutes: stepMinutes },
  });
  return data;
}

// Bước 2 — Xem chi tiết theo đơn vị khai thác -> hệ thống hiển thị.
export async function getApiUsageConsumers({ windowMinutes = 60, consumerCode = null } = {}) {
  const { data } = await apiGatewayClient.get("/api-usage/consumers", {
    params: { window_minutes: windowMinutes, consumer_code: consumerCode || undefined },
  });
  return data;
}

// Bước 3 — Cảnh báo khi API có bất thường -> Alertmanager gửi cảnh báo.
// (dùng để mô phỏng thủ công 1 lượt gọi webhook từ Alertmanager, phục vụ
// demo/kiểm thử khi chưa có Alertmanager thật cấu hình trỏ về đây)
export async function simulateAlertmanagerWebhook(payload) {
  const { data } = await apiGatewayClient.post("/alerts/webhook", payload);
  return data;
}

export async function listAnomalyAlerts({ status = null, severity = null, consumerCode = null } = {}) {
  const { data } = await apiGatewayClient.get("/alerts", {
    params: {
      status: status || undefined,
      severity: severity || undefined,
      consumer_code: consumerCode || undefined,
    },
  });
  return data;
}

export async function getAnomalyAlert(alertId) {
  const { data } = await apiGatewayClient.get(`/alerts/${alertId}`);
  return data;
}