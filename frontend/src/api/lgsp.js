import { apiGatewayClient } from "./apiCatalog.js";

// UC-065 — Cung cấp API qua LGSP. Dùng chung `apiGatewayClient` (đã trỏ
// tới api-gateway-service qua proxy `/api/api-gateway`, xem vite.config.js)
// — cùng service đã phục vụ UC-058..064. Không cần proxy dev mới.

// Bước 1+2+3 — Cổng LGSP chuyển tiếp yêu cầu; Cổng API kiểm tra chứng thư
// mTLS (số hiệu chứng thư truyền qua header `X-Client-Cert-Serial`) trước
// khi thực thi; LUÔN trả về phong bì phản hồi chuẩn LGSP (HTTP 200, kể cả
// khi `response_code` khác "00" do bị từ chối/lỗi).
export async function callLgspApi(certSerial, { requestId, serviceCode, payload = {} }) {
  const { data } = await apiGatewayClient.post(
    "/lgsp/request",
    { request_id: requestId, service_code: serviceCode, payload },
    { headers: certSerial ? { "X-Client-Cert-Serial": certSerial } : {} }
  );
  return data;
}

// Tra cứu `audit.audit_log` (lọc sẵn api_type=LGSP phía backend) — hỗ trợ
// Quản trị API xem lại lịch sử tích hợp qua Cổng LGSP.
export async function listLgspAuditLogs({ consumerCode = null, status = null, limit = 200 } = {}) {
  const { data } = await apiGatewayClient.get("/lgsp/audit-logs", {
    params: {
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
      ...(status ? { status } : {}),
      limit,
    },
  });
  return data;
}