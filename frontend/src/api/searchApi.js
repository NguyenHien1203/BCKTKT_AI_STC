import { apiGatewayClient } from "./apiCatalog.js";

// UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ. Dùng chung
// `apiGatewayClient` (đã trỏ tới api-gateway-service qua proxy
// `/api/api-gateway`, xem vite.config.js) — cùng service đã phục vụ
// UC-058..065. Không cần proxy dev mới.

// Bước 1+2+3 — QLVBĐH gọi Search API. Khoá API truyền qua header
// `X-API-Key` (KHÔNG nằm trong body). `userDonViCode`/`userSecurityLevel`
// là PHẠM VI CỦA NGƯỜI DÙNG CUỐI mà QLVBĐH gọi thay (khác phạm vi/scope
// của bản thân khoá API) — hệ thống tìm kiếm vector + BM25, lọc theo
// quyền của khoá rồi lọc tiếp theo phạm vi người dùng này, trả kết quả
// kèm dẫn nguồn.
export async function callSearchApi(
  rawApiKey,
  { query, topK = 10, userDonViCode = "", userSecurityLevel = "PUBLIC" }
) {
  const { data } = await apiGatewayClient.post(
    "/search-api/query",
    {
      query,
      top_k: topK,
      user_don_vi_code: userDonViCode || null,
      user_security_level: userSecurityLevel,
    },
    { headers: { "X-API-Key": rawApiKey } }
  );
  return data;
}

// Tra cứu audit.audit_log (hỗ trợ Quản trị API xem lại lịch sử lời gọi
// Search API, kể cả các lượt bị từ chối).
export async function listSearchApiAuditLogs({
  apiType = null,
  consumerCode = null,
  status = null,
  limit = 200,
} = {}) {
  const { data } = await apiGatewayClient.get("/search-api/audit-logs", {
    params: {
      ...(apiType ? { api_type: apiType } : {}),
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
      ...(status ? { status } : {}),
      limit,
    },
  });
  return data;
}
