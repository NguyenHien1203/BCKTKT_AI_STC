import { ingestionClient } from "./dataSources.js";

// UC-022: Tiếp nhận file thủ công TABMIS (upload). Dùng chung
// `ingestionClient` (baseURL "/api/ingestion") vì cùng thuộc ingestion-service.

// ---------- Bước 1: Tải biểu mẫu Excel ----------

export async function downloadUploadTemplate(datasetId) {
  const { data, headers } = await ingestionClient.get("/tabmis-intake/template", {
    params: { dataset_id: datasetId },
    responseType: "blob",
  });
  return { blob: data, contentType: headers["content-type"] };
}

// ---------- Bước 2-4: Tải tệp lên ----------

export async function uploadTabmisFile({ datasetId, uploadedBy, file }) {
  const form = new FormData();
  form.append("dataset_id", datasetId);
  form.append("uploaded_by", uploadedBy);
  form.append("file", file);
  const { data } = await ingestionClient.post("/tabmis-intake/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ---------- Xem lại phiên tiếp nhận ----------

export async function listTabmisIntakeSessions({ datasetId = null, status = null } = {}) {
  const { data } = await ingestionClient.get("/tabmis-intake", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getTabmisIntakeSession(id) {
  const { data } = await ingestionClient.get(`/tabmis-intake/${id}`);
  return data;
}

// ---------- UC-023: Xem trạng thái + sửa lỗi intake TABMIS ----------

// Bước 1: Xem trạng thái tiếp nhận -> hệ thống hiển thị máy trạng thái.
export async function getTabmisIntakeStatus(id) {
  const { data } = await ingestionClient.get(`/tabmis-intake/${id}/status`);
  return data;
}

// Bước 2: Xem chi tiết lỗi dòng -> hệ thống hiển thị các dòng sai.
export async function getTabmisIntakeRowErrors(id) {
  const { data } = await ingestionClient.get(`/tabmis-intake/${id}/row-errors`);
  return data;
}

// Bước 3: Sửa và tải lại tệp đã chỉnh -> hệ thống kiểm tra lại.
export async function reuploadTabmisIntakeFile({ sessionId, uploadedBy, file }) {
  const form = new FormData();
  form.append("uploaded_by", uploadedBy);
  form.append("file", file);
  const { data } = await ingestionClient.post(`/tabmis-intake/${sessionId}/reupload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}