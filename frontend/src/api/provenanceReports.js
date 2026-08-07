import { dataQualityClient } from "./parsingJobs.js";

// UC-046 (Xuất báo cáo nguồn gốc dữ liệu) dùng chung data-quality-service
// với UC-029/.../045 nên dùng lại `dataQualityClient` (baseURL
// "/api/data-quality"), không cần proxy dev mới. Tái sử dụng NGUYÊN VẸN
// lõi truy vết UC-045 (`api/recordLineage.js`), chỉ gộp theo phạm vi.

export const PROVENANCE_SCOPE_TYPES = ["DATASET", "RECORD", "SOURCE"];

export const PROVENANCE_SCOPE_LABELS = {
  DATASET: "Tập dữ liệu",
  RECORD: "Bản ghi",
  SOURCE: "Nguồn",
};

/**
 * Bước 1 "Chọn phạm vi (tập dữ liệu / bản ghi / nguồn)" + bước 2 "Sinh
 * báo cáo nguồn gốc dữ liệu": hệ thống hiển thị trước dạng JSON (chưa
 * kết xuất PDF).
 */
export async function previewProvenanceReport({
  scopeType,
  scopeValue,
  limit = null,
  includeStepDetails = null,
}) {
  const { data } = await dataQualityClient.get("/provenance-reports/preview", {
    params: {
      scope_type: scopeType,
      scope_value: scopeValue,
      ...(limit ? { limit } : {}),
      ...(includeStepDetails !== null && includeStepDetails !== undefined
        ? { include_step_details: includeStepDetails }
        : {}),
    },
  });
  return data;
}

/**
 * Bước 2 "Sinh báo cáo nguồn gốc dữ liệu" -> "Hệ thống kết xuất PDF" ->
 * bước 3 "Kết xuất PDF" -> "Hệ thống trả file": sinh báo cáo rồi tải
 * file PDF trực tiếp về máy người dùng.
 */
export async function exportProvenanceReportPdf({
  scopeType,
  scopeValue,
  limit = null,
  includeStepDetails = null,
}) {
  const response = await dataQualityClient.get("/provenance-reports/export", {
    params: {
      scope_type: scopeType,
      scope_value: scopeValue,
      ...(limit ? { limit } : {}),
      ...(includeStepDetails !== null && includeStepDetails !== undefined
        ? { include_step_details: includeStepDetails }
        : {}),
    },
    responseType: "blob",
  });

  const blob = new Blob([response.data], { type: "application/pdf" });
  const url = window.URL.createObjectURL(blob);
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `bao-cao-nguon-goc-du-lieu-${scopeType}-${scopeValue}.pdf`;

  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return filename;
}