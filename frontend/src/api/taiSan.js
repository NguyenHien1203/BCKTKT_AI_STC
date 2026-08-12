import { reportingClient } from "./dashboards.js";

// ---------- UC-054: Tra cứu dữ liệu tài sản ----------

export async function searchTaiSan({
  donViCode = "",
  nhomTaiSanCode = "",
  trangThai = "",
  page = 1,
  pageSize = 20,
}) {
  const { data } = await reportingClient.get("/tai-san", {
    params: {
      ...(donViCode ? { don_vi_code: donViCode } : {}),
      ...(nhomTaiSanCode ? { nhom_tai_san_code: nhomTaiSanCode } : {}),
      ...(trangThai ? { trang_thai: trangThai } : {}),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getTaiSanDetail(taiSanId) {
  const { data } = await reportingClient.get(`/tai-san/${taiSanId}`);
  return data;
}

// [Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-054] Nạp/cập nhật 1
// bản ghi tài sản vào curated.dm_tai_san, dùng khi chưa có pipeline công
// bố dữ liệu tự động nối vào bảng này.
export async function seedTaiSan(payload) {
  const { data } = await reportingClient.post("/tai-san/seed", payload);
  return data;
}