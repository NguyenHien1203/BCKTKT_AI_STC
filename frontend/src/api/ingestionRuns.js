import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Bước 1: Xem lịch sử chạy ----------

export async function listRunHistory({
  datasetId = null,
  scheduledTaskId = null,
  status = null,
  dateFrom = null,
  dateTo = null,
} = {}) {
  const { data } = await ingestionClient.get("/ingestion-runs", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(scheduledTaskId ? { scheduled_task_id: scheduledTaskId } : {}),
      ...(status ? { status } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
  });
  return data;
}

// ---------- Bước 2: Xem lịch đầy đủ dữ liệu (heatmap) ----------

export async function getDataCalendar({ datasetId, dateFrom, dateTo }) {
  const { data } = await ingestionClient.get("/ingestion-runs/calendar", {
    params: { dataset_id: datasetId, date_from: dateFrom, date_to: dateTo },
  });
  return data;
}

// ---------- Bước 3: Xem chi tiết phiên cụ thể ----------

export async function getRunDetail(runId) {
  const { data } = await ingestionClient.get(`/ingestion-runs/${runId}`);
  return data;
}

// ---------- Ghi nhận vòng đời phiên (hạ tầng dùng bởi UC-021/UC-025) ----------

export async function startIngestionRun(payload) {
  const { data } = await ingestionClient.post("/ingestion-runs", payload);
  return data;
}

export async function appendIngestionRunLog(runId, { level = "INFO", message, timestamp = null }) {
  const { data } = await ingestionClient.post(`/ingestion-runs/${runId}/logs`, {
    level,
    message,
    timestamp,
  });
  return data;
}

export async function completeIngestionRun(runId, payload) {
  const { data } = await ingestionClient.post(`/ingestion-runs/${runId}/complete`, payload);
  return data;
}