import { reportingClient } from "./dashboards.js";

// ---------- UC-053: Tra cứu dữ liệu văn bản ----------

export async function searchDocuments({
  userId,
  keyword = "",
  coQuan = "",
  loaiVanBan = "",
  ngayFrom = "",
  ngayTo = "",
  page = 1,
  pageSize = 20,
}) {
  const { data } = await reportingClient.get("/documents", {
    params: {
      user_id: userId,
      ...(keyword ? { keyword } : {}),
      ...(coQuan ? { co_quan: coQuan } : {}),
      ...(loaiVanBan ? { loai_van_ban: loaiVanBan } : {}),
      ...(ngayFrom ? { ngay_from: ngayFrom } : {}),
      ...(ngayTo ? { ngay_to: ngayTo } : {}),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getDocumentDetail(documentId, userId) {
  const { data } = await reportingClient.get(`/documents/${documentId}`, {
    params: { user_id: userId },
  });
  return data;
}

export function getDocumentFileUrl(documentId, userId) {
  // Dùng trực tiếp làm src cho <iframe>/<embed> — trình duyệt tự gọi qua
  // proxy /api/reporting (xem vite.config.js).
  return `/api/reporting/documents/${documentId}/file?user_id=${userId}`;
}

export async function fetchDocumentFileBlob(documentId, userId) {
  const { data } = await reportingClient.get(`/documents/${documentId}/file`, {
    params: { user_id: userId },
    responseType: "blob",
  });
  return data;
}

// [Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-053] Lập chỉ mục 1
// văn bản vào OpenSearch, dùng khi chưa có pipeline tự động (UC-024 ->
// OCR UC-030) nối vào OpenSearch thật.
export async function indexDocument(payload) {
  const { data } = await reportingClient.post("/documents/index", payload);
  return data;
}