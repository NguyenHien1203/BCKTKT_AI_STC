import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") vì cùng thuộc
// ingestion-service.

// ---------- Bước 1: Xem điểm kiểm tra (checkpoint) đọc từ ingestion.runs ----------

export async function getIncrementalSyncCheckpoint(datasetId) {
  const { data } = await ingestionClient.get(`/incremental-sync/${datasetId}/checkpoint`);
  return data;
}

// ---------- Bước 1-4: Kích hoạt 1 phiên đồng bộ tăng dần ----------

export async function runIncrementalSync(datasetId, { scheduledTaskId = null, trigger = "MANUAL" } = {}) {
  const { data } = await ingestionClient.post(`/incremental-sync/${datasetId}/run`, {
    scheduled_task_id: scheduledTaskId,
    trigger,
  });
  return data;
}