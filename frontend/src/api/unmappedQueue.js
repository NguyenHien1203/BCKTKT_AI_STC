import { dataQualityClient } from "./parsingJobs.js";

// UC-032 (Xử lý hàng đợi chưa ánh xạ) dùng chung data-quality-service
// nên dùng lại `dataQualityClient` (baseURL "/api/data-quality") của
// UC-029/030/031 -- không cần proxy dev mới.

export async function listUnmappedQueueItems({
  datasetId = null,
  fieldName = null,
  status = "PENDING",
} = {}) {
  const { data } = await dataQualityClient.get("/unmapped-queue", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(fieldName ? { field_name: fieldName } : {}),
      // Truyền chuỗi rỗng để xem TẤT CẢ (PENDING + RESOLVED).
      status: status === null ? "" : status,
    },
  });
  return data;
}

export async function getUnmappedQueueItem(id) {
  const { data } = await dataQualityClient.get(`/unmapped-queue/${id}`);
  return data;
}

/**
 * Bước 2 "Xử lý giá trị (ánh xạ / tạo mục mới / từ chối)" + bước 3
 * "Ánh xạ hàng loạt các giá trị tương tự" (applyToSimilar=true).
 */
export async function resolveUnmappedQueueItem(
  id,
  { action, standardValue = null, reason = null, applyToSimilar = false },
) {
  const { data } = await dataQualityClient.post(`/unmapped-queue/${id}/resolve`, {
    action,
    ...(standardValue ? { standard_value: standardValue } : {}),
    ...(reason ? { reason } : {}),
    apply_to_similar: applyToSimilar,
  });
  return data;
}