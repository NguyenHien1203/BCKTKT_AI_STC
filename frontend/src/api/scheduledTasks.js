import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Cấu hình tác vụ điều phối ----------

export async function listScheduledTasks({ datasetId = null, onlyEnabled = false } = {}) {
  const { data } = await ingestionClient.get("/scheduled-tasks", {
    params: {
      only_enabled: onlyEnabled,
      ...(datasetId ? { dataset_id: datasetId } : {}),
    },
  });
  return data;
}

export async function getScheduledTask(id) {
  const { data } = await ingestionClient.get(`/scheduled-tasks/${id}`);
  return data;
}

export async function configureScheduledTask(payload) {
  const { data } = await ingestionClient.post("/scheduled-tasks", payload);
  return data;
}

export async function updateScheduledTaskConfig(id, payload) {
  const { data } = await ingestionClient.put(`/scheduled-tasks/${id}`, payload);
  return data;
}

// ---------- Bật / tắt tác vụ điều phối ----------

export async function enableScheduledTask(id) {
  const { data } = await ingestionClient.post(`/scheduled-tasks/${id}/enable`);
  return data;
}

export async function disableScheduledTask(id) {
  const { data } = await ingestionClient.post(`/scheduled-tasks/${id}/disable`);
  return data;
}

// ---------- Hệ thống cập nhật trạng thái thực thi ----------

export async function recordScheduledTaskRunStatus(id, { status, message = "", runAt = null }) {
  const { data } = await ingestionClient.post(`/scheduled-tasks/${id}/status`, {
    status,
    message,
    run_at: runAt,
  });
  return data;
}