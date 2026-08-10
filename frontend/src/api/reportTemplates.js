import { reportingClient } from "./dashboards.js";

// ---------- UC-049: Chọn báo cáo theo mẫu + cấu hình bộ lọc ----------

export async function listReportTemplates({ onlyActive = true, category = null } = {}) {
  const { data } = await reportingClient.get("/report-templates", {
    params: {
      only_active: onlyActive,
      ...(category ? { category } : {}),
    },
  });
  return data;
}

export async function getReportTemplate(id) {
  const { data } = await reportingClient.get(`/report-templates/${id}`);
  return data;
}

export async function registerReportTemplate(payload) {
  const { data } = await reportingClient.post("/report-templates", payload);
  return data;
}

export async function activateReportTemplate(id) {
  const { data } = await reportingClient.post(`/report-templates/${id}/activate`);
  return data;
}

export async function deactivateReportTemplate(id) {
  const { data } = await reportingClient.post(`/report-templates/${id}/deactivate`);
  return data;
}

export async function previewReportTemplate(id, sampleSize = 5) {
  const { data } = await reportingClient.get(`/report-templates/${id}/preview`, {
    params: { sample_size: sampleSize },
  });
  return data;
}

export async function saveReportFilterConfig(
  templateId,
  { userId, year, periodType, periodValue = null, orgUnitCode = null, sector = null }
) {
  const { data } = await reportingClient.put(`/report-templates/${templateId}/filter-config`, {
    user_id: userId,
    year,
    period_type: periodType,
    period_value: periodValue,
    org_unit_code: orgUnitCode || null,
    sector: sector || null,
  });
  return data;
}

export async function getReportFilterConfig(templateId, userId) {
  const { data } = await reportingClient.get(`/report-templates/${templateId}/filter-config`, {
    params: { user_id: userId },
  });
  return data;
}

export async function listMyReportFilterConfigs(userId) {
  const { data } = await reportingClient.get("/report-templates/filter-configs/mine", {
    params: { user_id: userId },
  });
  return data;
}