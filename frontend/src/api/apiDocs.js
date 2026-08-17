import { apiGatewayClient } from "./apiCatalog";

// ---------- UC-063: Cung cấp cổng tài liệu API ----------
// Đơn vị khai thác (QLVBĐH, IOC, LGSP) truy cập cổng Swagger/Redoc ->
// hệ thống hiển thị UI -> Xem.

// Đường dẫn tương đối qua proxy dev `/api/api-gateway` (xem vite.config.js).
// Dùng trực tiếp trong <iframe>/thẻ <a target="_blank"> ở ApiDocsPage.
export const API_DOCS_SWAGGER_URL = `${apiGatewayClient.defaults.baseURL}/api-docs/swagger`;
export const API_DOCS_REDOC_URL = `${apiGatewayClient.defaults.baseURL}/api-docs/redoc`;
export const API_DOCS_OPENAPI_JSON_URL = `${apiGatewayClient.defaults.baseURL}/api-docs/openapi.json`;

export async function getPublishedApiDocsCatalog() {
  const { data } = await apiGatewayClient.get("/api-docs/catalog");
  return data;
}

export async function getApiDocsOpenApiSpec() {
  const { data } = await apiGatewayClient.get("/api-docs/openapi.json");
  return data;
}