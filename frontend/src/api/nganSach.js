import { reportingClient } from "./dashboards.js";

// ---------- UC-056: Tra cứu dữ liệu ngân sách ----------

export async function searchNganSach({
  donVi = "",
  khoanMuc = "",
  kyFrom = "",
  kyTo = "",
  page = 1,
  pageSize = 20,
}) {
  const { data } = await reportingClient.get("/ngan-sach", {
    params: {
      ...(donVi ? { don_vi: donVi } : {}),
      ...(khoanMuc ? { khoan_muc: khoanMuc } : {}),
      ...(kyFrom ? { ky_from: kyFrom } : {}),
      ...(kyTo ? { ky_to: kyTo } : {}),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

// Bước 4-5: "Xem chi tiết theo đơn vị/khoản mục -> Hệ thống re-query".
export async function getNganSachDetail({ donViCode, khoanMucCode }) {
  const { data } = await reportingClient.get("/ngan-sach/detail", {
    params: {
      don_vi_code: donViCode,
      khoan_muc_code: khoanMucCode,
    },
  });
  return data;
}

// [Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-056] Nạp 1 dòng số
// liệu ngân sách vào curated.dm_ngan_sach, dùng khi chưa có pipeline
// UC-041 tự động công bố dữ liệu ngân sách thật.
export async function indexNganSachRecord(payload) {
  const { data } = await reportingClient.post("/ngan-sach/index", payload);
  return data;
}