import { dataQualityClient } from "./parsingJobs.js";

// UC-040 (Xử lý ngoại lệ chất lượng) dùng chung data-quality-service
// với UC-029/.../039 nên dùng lại `dataQualityClient` (baseURL
// "/api/data-quality") -- không cần proxy dev mới.

/** Bước 1 "Xem hàng đợi ngoại lệ" -- hệ thống hiển thị (mặc định PENDING). */
export async function listQualityExceptions({ datasetId = null, status = "PENDING" } = {}) {
  const { data } = await dataQualityClient.get("/quality-exceptions", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      // Truyền chuỗi rỗng để xem TẤT CẢ (PENDING + RESOLVED).
      status: status === null ? "" : status,
    },
  });
  return data;
}

export async function getQualityException(id) {
  const { data } = await dataQualityClient.get(`/quality-exceptions/${id}`);
  return data;
}

/**
 * Bước 2 "Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn)" -- hệ
 * thống lưu quyết định. `action`: FIX / REJECT / REQUEST_SOURCE.
 */
export async function resolveQualityException(
  id,
  { action, correctedFields = null, reason = null },
) {
  const { data } = await dataQualityClient.post(`/quality-exceptions/${id}/resolve`, {
    action,
    ...(correctedFields ? { corrected_fields: correctedFields } : {}),
    ...(reason ? { reason } : {}),
  });
  return data;
}

/**
 * Bước 3 "Xử lý hàng loạt ngoại lệ cùng loại" -- hệ thống áp dụng đồng
 * loạt cùng 1 quyết định cho toàn bộ ngoại lệ PENDING của 1 tập dữ
 * liệu có cùng `ruleType` không đạt.
 */
export async function batchResolveQualityExceptions({
  datasetId = null,
  ruleType,
  action,
  correctedFields = null,
  reason = null,
}) {
  const { data } = await dataQualityClient.post("/quality-exceptions/batch-resolve", {
    ...(datasetId !== null ? { dataset_id: datasetId } : {}),
    rule_type: ruleType,
    action,
    ...(correctedFields ? { corrected_fields: correctedFields } : {}),
    ...(reason ? { reason } : {}),
  });
  return data;
}