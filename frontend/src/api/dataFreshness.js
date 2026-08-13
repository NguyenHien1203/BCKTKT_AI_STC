import { reportingClient } from "./dashboards.js";

// ---------- UC-057: Hiển thị độ mới dữ liệu ----------

// Bước 1-2: "Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển -> Hệ
// thống truy vấn view curated.data_freshness".
export async function getDataFreshnessSummary() {
  const { data } = await reportingClient.get("/data-freshness/summary");
  return data;
}

// Bước 3-4: "Xem chi tiết last_sync + độ đầy đủ theo nguồn -> Hệ thống
// hiển thị bảng".
export async function listDataFreshness() {
  const { data } = await reportingClient.get("/data-freshness");
  return data;
}

export async function getDataFreshnessForSource(nguonCode) {
  const { data } = await reportingClient.get(`/data-freshness/${nguonCode}`);
  return data;
}

// [Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-057] Ghi nhận/cập
// nhật độ mới của 1 nguồn vào curated.data_freshness, dùng khi chưa có
// pipeline tự động (UC-025/UC-041) tự cập nhật bảng này.
export async function indexDataFreshnessRecord(payload) {
  const { data } = await reportingClient.post("/data-freshness/index", payload);
  return data;
}