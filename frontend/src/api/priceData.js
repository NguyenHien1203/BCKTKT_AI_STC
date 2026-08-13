import { reportingClient } from "./dashboards.js";

// ---------- UC-055: Tra cứu dữ liệu giá ----------

export async function searchPriceData({
  matHang = "",
  diaBan = "",
  kyFrom = "",
  kyTo = "",
  page = 1,
  pageSize = 20,
}) {
  const { data } = await reportingClient.get("/price-data", {
    params: {
      ...(matHang ? { mat_hang: matHang } : {}),
      ...(diaBan ? { dia_ban: diaBan } : {}),
      ...(kyFrom ? { ky_from: kyFrom } : {}),
      ...(kyTo ? { ky_to: kyTo } : {}),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getPriceTrend({ matHang = "", diaBan = "", kyFrom = "", kyTo = "" }) {
  const { data } = await reportingClient.get("/price-data/trend", {
    params: {
      ...(matHang ? { mat_hang: matHang } : {}),
      ...(diaBan ? { dia_ban: diaBan } : {}),
      ...(kyFrom ? { ky_from: kyFrom } : {}),
      ...(kyTo ? { ky_to: kyTo } : {}),
    },
  });
  return data;
}

// [Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-055] Nạp 1 dòng dữ
// liệu giá vào curated.dm_gia, dùng khi chưa có pipeline UC-041 tự động
// công bố dữ liệu giá thật.
export async function indexPriceRecord(payload) {
  const { data } = await reportingClient.post("/price-data/index", payload);
  return data;
}