import { apiGatewayClient } from "./apiCatalog.js";

// Dùng chung `apiGatewayClient` (đã trỏ tới api-gateway-service qua proxy
// `/api/api-gateway`, xem vite.config.js) — cùng service đã phục vụ
// UC-058/059/060/061.

// ---------- UC-062: Quản lý chứng thư / mTLS cho đơn vị khai thác ----------

// Bước 1 — Đăng ký chứng thư của đơn vị khai thác -> hệ thống lưu vào kho
// tin cậy.
export async function registerMtlsCertificate(payload) {
  const { data } = await apiGatewayClient.post("/mtls-certificates", payload);
  return data;
}

export async function listMtlsCertificates({ consumerCode = null, status = null } = {}) {
  const { data } = await apiGatewayClient.get("/mtls-certificates", {
    params: {
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getMtlsCertificate(id) {
  const { data } = await apiGatewayClient.get(`/mtls-certificates/${id}`);
  return data;
}

// Bước 2 — Luân chuyển chứng thư -> hệ thống cập nhật.
export async function rotateMtlsCertificate(id, payload) {
  const { data } = await apiGatewayClient.post(`/mtls-certificates/${id}/rotate`, payload);
  return data;
}

// Bước 3 — Thu hồi chứng thư -> hệ thống thêm vào CRL.
export async function revokeMtlsCertificate(id, reason = "") {
  const { data } = await apiGatewayClient.post(`/mtls-certificates/${id}/revoke`, { reason });
  return data;
}

export async function getCertificateRevocationList({ consumerCode = null } = {}) {
  const { data } = await apiGatewayClient.get("/mtls-certificates/crl", {
    params: {
      ...(consumerCode ? { consumer_code: consumerCode } : {}),
    },
  });
  return data;
}

export async function checkCertificateRevoked(serialNumber) {
  const { data } = await apiGatewayClient.get(
    `/mtls-certificates/crl/${encodeURIComponent(serialNumber)}/check`
  );
  return data;
}