import { apiGatewayClient } from "./apiCatalog.js";

// UC-064 — Cung cấp Data API cho IOC. Dùng chung `apiGatewayClient` (đã
// trỏ tới api-gateway-service qua proxy `/api/api-gateway`, xem
// vite.config.js) — cùng service đã phục vụ UC-058..063. Không cần proxy
// dev mới.

// Bước 1+2+3 — IOC gọi Data API tổng hợp. Khoá API truyền qua header
// `X-API-Key` (KHÔNG nằm trong body) — Cổng API kiểm tra khoá + phạm vi +
// giới hạn tần suất trước khi thực thi qua Lớp ngữ nghĩa.
export async function callDataApi(rawApiKey, { datasetCode, filters = {} }) {
  const { data } = await apiGatewayClient.post(
    "/data-api/query",
    { dataset_code: datasetCode, filters },
    { headers: { "X-API-Key": rawApiKey } }
  );
  return data;
}

// Bước 3 — Tra cứu audit.audit_log (hỗ trợ Quản trị API xem lại lịch sử
// lời gọi Data API, kể cả các lượt bị từ chối).
export async function listDataApiAuditLogs({
  apiType = null,
  consumerCode = null,
  status = null,
  limit = 200,
} = {}) {
  const { data } = await apiGatewayClient.get("/data-api/audit-logs", {
    params: {
      ...(apiType ? { api_type: apiType } : {}),
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
      ...(status ? { status } : {}),
      limit,
    },
  });
  return data;
}