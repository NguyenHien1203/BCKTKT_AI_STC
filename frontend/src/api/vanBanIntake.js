import { ingestionClient } from "./dataSources.js";

// UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (upload định kỳ). Dùng chung
// `ingestionClient` (baseURL "/api/ingestion") vì cùng thuộc ingestion-service.

// Nộp văn bản: nhập siêu dữ liệu + đính kèm tệp PDF/bản quét trong 1 lần
// gọi -> hệ thống khử trùng lặp theo so_ky_hieu, lưu staging.stg_van_ban +
// MinIO (raw-documents), kích hoạt sự kiện ocr.requested.
export async function submitVanBanDocument({
  dataSourceId,
  soKyHieu,
  loaiVanBan,
  trichYeu,
  ngayBanHanh,
  donViBanHanh,
  uploadedBy,
  file,
}) {
  const form = new FormData();
  form.append("data_source_id", dataSourceId);
  form.append("so_ky_hieu", soKyHieu);
  form.append("loai_van_ban", loaiVanBan);
  form.append("trich_yeu", trichYeu);
  form.append("ngay_ban_hanh", ngayBanHanh);
  form.append("don_vi_ban_hanh", donViBanHanh);
  form.append("uploaded_by", uploadedBy);
  form.append("file", file);
  const { data } = await ingestionClient.post("/qlvbdh-intake/documents", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listVanBanDocuments({ dataSourceId = null, status = null } = {}) {
  const { data } = await ingestionClient.get("/qlvbdh-intake/documents", {
    params: {
      ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getVanBanDocument(id) {
  const { data } = await ingestionClient.get(`/qlvbdh-intake/documents/${id}`);
  return data;
}