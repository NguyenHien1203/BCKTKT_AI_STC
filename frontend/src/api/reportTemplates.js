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

// ---------- UC-050: Sinh + kết xuất báo cáo ----------
// Nếu không truyền year/periodType, hệ thống dùng lại cấu hình bộ lọc đã
// lưu ở UC-049 (saveReportFilterConfig).

function _reportFilterParams({
  userId,
  year = null,
  periodType = null,
  periodValue = null,
  orgUnitCode = null,
  sector = null,
}) {
  return {
    user_id: userId,
    ...(year ? { year } : {}),
    ...(periodType ? { period_type: periodType } : {}),
    ...(periodValue ? { period_value: periodValue } : {}),
    ...(orgUnitCode ? { org_unit_code: orgUnitCode } : {}),
    ...(sector ? { sector } : {}),
  };
}

/** Bước 1 — "Sinh báo cáo theo mẫu + bộ lọc": hệ thống truy vấn Lớp ngữ
 * nghĩa + kết xuất. Trả về xem trước dạng JSON (chưa xuất file). */
export async function generateReport(templateId, filters) {
  const { data } = await reportingClient.post(
    `/report-templates/${templateId}/reports/generate`,
    null,
    { params: _reportFilterParams(filters) }
  );
  return data;
}

async function _downloadReportFile(templateId, extension, filters, mimeType) {
  const response = await reportingClient.get(
    `/report-templates/${templateId}/reports/export.${extension}`,
    { params: _reportFilterParams(filters), responseType: "blob" }
  );

  const blob = new Blob([response.data], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `bao-cao-${templateId}.${extension}`;

  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return filename;
}

/** Bước 2 — "Kết xuất PDF -> Hệ thống trả file". */
export async function exportReportPdf(templateId, filters) {
  return _downloadReportFile(templateId, "pdf", filters, "application/pdf");
}

/** Bước 3 — "Kết xuất Excel -> Hệ thống trả file". */
export async function exportReportExcel(templateId, filters) {
  return _downloadReportFile(
    templateId,
    "xlsx",
    filters,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  );
}

/** Lịch sử các lượt kết xuất báo cáo (PDF/Excel) của người dùng cho 1 mẫu. */
export async function listGeneratedReportLogs(templateId, userId) {
  const { data } = await reportingClient.get(`/report-templates/${templateId}/reports/logs`, {
    params: { user_id: userId },
  });
  return data;
}

// ---------- UC-051: Cấu hình báo cáo theo lịch ----------
// Flow: Cấu hình lịch (hàng ngày/hàng tuần/hàng tháng) -> hệ thống lưu lịch.
// Cấu hình người nhận (email) -> hệ thống lưu.
// Hệ thống tự động sinh + gửi email báo cáo theo lịch (tác vụ định kỳ/cron).

export async function listReportSchedules(templateId, userId) {
  const { data } = await reportingClient.get(`/report-templates/${templateId}/schedules`, {
    params: { user_id: userId },
  });
  return data;
}

/** Bước 1 — "Cấu hình lịch (hàng ngày/hàng tuần/hàng tháng)" -> hệ thống lưu lịch. */
export async function createReportSchedule(
  templateId,
  {
    userId,
    frequency,
    timeOfDay,
    format = "PDF",
    dayOfWeek = null,
    dayOfMonth = null,
    year = null,
    periodType = null,
    periodValue = null,
    orgUnitCode = null,
    sector = null,
  }
) {
  const { data } = await reportingClient.post(`/report-templates/${templateId}/schedules`, {
    user_id: userId,
    frequency,
    time_of_day: timeOfDay,
    format,
    day_of_week: dayOfWeek,
    day_of_month: dayOfMonth,
    year,
    period_type: periodType,
    period_value: periodValue,
    org_unit_code: orgUnitCode || null,
    sector: sector || null,
  });
  return data;
}

export async function updateReportSchedule(
  templateId,
  scheduleId,
  {
    frequency,
    timeOfDay,
    format = "PDF",
    dayOfWeek = null,
    dayOfMonth = null,
    year = null,
    periodType = null,
    periodValue = null,
    orgUnitCode = null,
    sector = null,
  }
) {
  const { data } = await reportingClient.put(
    `/report-templates/${templateId}/schedules/${scheduleId}`,
    {
      frequency,
      time_of_day: timeOfDay,
      format,
      day_of_week: dayOfWeek,
      day_of_month: dayOfMonth,
      year,
      period_type: periodType,
      period_value: periodValue,
      org_unit_code: orgUnitCode || null,
      sector: sector || null,
    }
  );
  return data;
}

export async function enableReportSchedule(templateId, scheduleId) {
  const { data } = await reportingClient.post(
    `/report-templates/${templateId}/schedules/${scheduleId}/enable`
  );
  return data;
}

export async function disableReportSchedule(templateId, scheduleId) {
  const { data } = await reportingClient.post(
    `/report-templates/${templateId}/schedules/${scheduleId}/disable`
  );
  return data;
}

// ---------- UC-051 bước 2: Cấu hình người nhận (email) -> hệ thống lưu ----------

export async function listReportScheduleRecipients(templateId, scheduleId) {
  const { data } = await reportingClient.get(
    `/report-templates/${templateId}/schedules/${scheduleId}/recipients`
  );
  return data;
}

export async function addReportScheduleRecipient(templateId, scheduleId, email) {
  const { data } = await reportingClient.post(
    `/report-templates/${templateId}/schedules/${scheduleId}/recipients`,
    { email }
  );
  return data;
}

export async function removeReportScheduleRecipient(templateId, scheduleId, email) {
  await reportingClient.delete(
    `/report-templates/${templateId}/schedules/${scheduleId}/recipients/${encodeURIComponent(email)}`
  );
}

// ---------- UC-051 bước 3: Hệ thống tự động sinh + gửi email báo cáo theo lịch ----------

/** Chạy thử ngay 1 lịch (mô phỏng đúng hành vi tác vụ định kỳ/cron khi tới hạn). */
export async function runReportScheduleNow(templateId, scheduleId) {
  const { data } = await reportingClient.post(
    `/report-templates/${templateId}/schedules/${scheduleId}/run-now`
  );
  return data;
}

export async function listReportScheduleRunLogs(templateId, scheduleId) {
  const { data } = await reportingClient.get(
    `/report-templates/${templateId}/schedules/${scheduleId}/logs`
  );
  return data;
}