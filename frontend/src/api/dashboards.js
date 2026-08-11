import axios from "axios";

// Qua Vite dev proxy (xem vite.config.js) -> reporting-service (port 8004).
// Khi build production, đổi baseURL này thành URL của APISIX Gateway thật.
export const reportingClient = axios.create({
  baseURL: "/api/reporting",
});

// ---------- UC-047: Xem Bảng điều khiển điều hành ----------

export async function listDashboards({ onlyActive = true, category = null } = {}) {
  const { data } = await reportingClient.get("/dashboards", {
    params: {
      only_active: onlyActive,
      ...(category ? { category } : {}),
    },
  });
  return data;
}

export async function getDashboard(id) {
  const { data } = await reportingClient.get(`/dashboards/${id}`);
  return data;
}

export async function registerDashboard(payload) {
  const { data } = await reportingClient.post("/dashboards", payload);
  return data;
}

export async function listFavoriteDashboards(userId) {
  const { data } = await reportingClient.get("/dashboards/favorites", {
    params: { user_id: userId },
  });
  return data;
}

// ---------- UC-047 (nâng cấp): Superset Embedded Dashboard SDK + Guest Token ----------

export async function getDashboardGuestToken(dashboardId, { userId, username, fullName } = {}) {
  const { data } = await reportingClient.get(`/dashboards/${dashboardId}/guest-token`, {
    params: {
      user_id: userId,
      ...(username ? { username } : {}),
      ...(fullName ? { full_name: fullName } : {}),
    },
  });
  return data;
}

export async function pinFavoriteDashboard(dashboardId, userId) {
  const { data } = await reportingClient.post(`/dashboards/${dashboardId}/favorite`, {
    user_id: userId,
  });
  return data;
}

export async function unpinFavoriteDashboard(dashboardId, userId) {
  await reportingClient.delete(`/dashboards/${dashboardId}/favorite`, {
    params: { user_id: userId },
  });
}

// ---------- UC-048: Áp bộ lọc + xem chi tiết Bảng điều khiển ----------

export async function listDashboardKpis(dashboardId, { onlyActive = true } = {}) {
  const { data } = await reportingClient.get(`/dashboards/${dashboardId}/kpis`, {
    params: { only_active: onlyActive },
  });
  return data;
}

export async function registerDashboardKpi(dashboardId, payload) {
  const { data } = await reportingClient.post(`/dashboards/${dashboardId}/kpis`, payload);
  return data;
}

export async function applyDashboardFilters(dashboardId, { year, orgUnitCode, sector }) {
  const { data } = await reportingClient.post(`/dashboards/${dashboardId}/filters/apply`, {
    year,
    org_unit_code: orgUnitCode || null,
    sector: sector || null,
  });
  return data;
}

export async function getKpiDetail(dashboardId, kpiCode, { year, orgUnitCode, sector }) {
  const { data } = await reportingClient.get(
    `/dashboards/${dashboardId}/kpis/${kpiCode}/detail`,
    {
      params: {
        year,
        ...(orgUnitCode ? { org_unit_code: orgUnitCode } : {}),
        ...(sector ? { sector } : {}),
      },
    }
  );
  return data;
}

export async function getKpiComparison(dashboardId, kpiCode, { year, orgUnitCode, sector }) {
  const { data } = await reportingClient.get(
    `/dashboards/${dashboardId}/kpis/${kpiCode}/comparison`,
    {
      params: {
        year,
        ...(orgUnitCode ? { org_unit_code: orgUnitCode } : {}),
        ...(sector ? { sector } : {}),
      },
    }
  );
  return data;
}

export async function requestKpiAiExplanation(
  dashboardId,
  kpiCode,
  { requestedBy, year, orgUnitCode, sector }
) {
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/kpis/${kpiCode}/ai-explanation`,
    {
      requested_by: requestedBy,
      year,
      org_unit_code: orgUnitCode || null,
      sector: sector || null,
    }
  );
  return data;
}

export async function listKpiAiExplanations(dashboardId, kpiCode) {
  const { data } = await reportingClient.get(
    `/dashboards/${dashboardId}/kpis/${kpiCode}/ai-explanations`
  );
  return data;
}

// ---------- UC-052: Đăng ký nhận cảnh báo dashboard ----------

export async function listDashboardAlertRules(dashboardId, { kpiCode = null } = {}) {
  const { data } = await reportingClient.get(`/dashboards/${dashboardId}/alert-rules`, {
    params: kpiCode ? { kpi_code: kpiCode } : {},
  });
  return data;
}

export async function configureDashboardAlertRule(dashboardId, payload) {
  // Bước 1 — "Cấu hình ngưỡng cảnh báo trên KPI" -> hệ thống lưu.
  const { data } = await reportingClient.post(`/dashboards/${dashboardId}/alert-rules`, {
    kpi_code: payload.kpiCode,
    user_id: payload.userId,
    operator: payload.operator,
    threshold_value: payload.thresholdValue,
    year: payload.year,
    org_unit_code: payload.orgUnitCode || null,
    sector: payload.sector || null,
  });
  return data;
}

export async function updateDashboardAlertRule(dashboardId, ruleId, payload) {
  const { data } = await reportingClient.put(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}`,
    {
      operator: payload.operator,
      threshold_value: payload.thresholdValue,
      year: payload.year,
      org_unit_code: payload.orgUnitCode || null,
      sector: payload.sector || null,
    }
  );
  return data;
}

export async function activateDashboardAlertRule(dashboardId, ruleId) {
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/activate`
  );
  return data;
}

export async function deactivateDashboardAlertRule(dashboardId, ruleId) {
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/deactivate`
  );
  return data;
}

export async function listDashboardAlertChannels(dashboardId, ruleId, { onlyActive = false } = {}) {
  const { data } = await reportingClient.get(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/channels`,
    { params: { only_active: onlyActive } }
  );
  return data;
}

export async function addDashboardAlertChannel(dashboardId, ruleId, { channelType, destination }) {
  // Bước 2 — "Chọn kênh nhận (email / Slack / Webhook)" -> hệ thống lưu.
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/channels`,
    { channel_type: channelType, destination }
  );
  return data;
}

export async function deactivateDashboardAlertChannel(dashboardId, ruleId, channelId) {
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/channels/${channelId}/deactivate`
  );
  return data;
}

export async function activateDashboardAlertChannel(dashboardId, ruleId, channelId) {
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/channels/${channelId}/activate`
  );
  return data;
}

export async function deleteDashboardAlertChannel(dashboardId, ruleId, channelId) {
  await reportingClient.delete(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/channels/${channelId}`
  );
}

export async function evaluateDashboardAlertRule(dashboardId, ruleId) {
  // Bước 3 — "Khi vượt ngưỡng -> Hệ thống gửi cảnh báo qua kênh đã chọn"
  // (chạy thử ngay, không cần chờ tác vụ định kỳ).
  const { data } = await reportingClient.post(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/evaluate`
  );
  return data;
}

export async function listDashboardAlertLogs(dashboardId, ruleId) {
  const { data } = await reportingClient.get(
    `/dashboards/${dashboardId}/alert-rules/${ruleId}/logs`
  );
  return data;
}

export async function listDashboardAlertRulesForUser(userId) {
  const { data } = await reportingClient.get("/dashboard-alerts/rules", {
    params: { user_id: userId },
  });
  return data;
}