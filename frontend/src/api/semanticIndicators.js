import { dataQualityClient } from "./parsingJobs.js";

// UC-043 (Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa) dùng chung
// data-quality-service với UC-029/.../042 nên dùng lại `dataQualityClient`
// (baseURL "/api/data-quality") -- không cần proxy dev mới.

export const INDICATOR_STATUSES = [
  { value: "DRAFT", label: "Nháp" },
  { value: "ACTIVE", label: "Đang dùng" },
  { value: "INACTIVE", label: "Ngừng dùng" },
];

/** Tra cứu — danh sách chỉ tiêu, lọc theo lĩnh vực/trạng thái. */
export async function listSemanticIndicators({ domain = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/semantic-indicators", {
    params: {
      ...(domain ? { domain } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getSemanticIndicator(id) {
  const { data } = await dataQualityClient.get(`/semantic-indicators/${id}`);
  return data;
}

/** Bước 1 "Tạo chỉ tiêu mới (tên, mô tả, biểu thức, lĩnh vực)" -- hệ thống lưu vào PostgreSQL. */
export async function createSemanticIndicator({
  name,
  expression,
  domain,
  description = null,
  createdBy = null,
  note = null,
}) {
  const { data } = await dataQualityClient.post("/semantic-indicators", {
    name,
    expression,
    domain,
    ...(description ? { description } : {}),
    ...(createdBy ? { created_by: createdBy } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 3 "Quản lý phiên bản chỉ tiêu" -- hệ thống lưu version + audit. */
export async function updateSemanticIndicator(
  id,
  {
    name = null,
    description = null,
    clearDescription = false,
    expression = null,
    domain = null,
    status = null,
    changedBy = null,
    note = null,
  },
) {
  const { data } = await dataQualityClient.put(`/semantic-indicators/${id}`, {
    ...(name !== null ? { name } : {}),
    ...(description !== null ? { description } : {}),
    clear_description: clearDescription,
    ...(expression !== null ? { expression } : {}),
    ...(domain !== null ? { domain } : {}),
    ...(status !== null ? { status } : {}),
    ...(changedBy ? { changed_by: changedBy } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}

export async function listSemanticIndicatorVersions(id) {
  const { data } = await dataQualityClient.get(`/semantic-indicators/${id}/versions`);
  return data;
}

export async function listSemanticIndicatorAuditLogs(id) {
  const { data } = await dataQualityClient.get(`/semantic-indicators/${id}/audit-logs`);
  return data;
}

/** Bước 2 "Kiểm thử chỉ tiêu trên truy vấn mẫu" -- hệ thống chạy và hiển thị kết quả. */
export async function testSemanticIndicator(id, { sampleRows, testedBy = null }) {
  const { data } = await dataQualityClient.post(`/semantic-indicators/${id}/test`, {
    sample_rows: sampleRows,
    ...(testedBy ? { tested_by: testedBy } : {}),
  });
  return data;
}

export async function listIndicatorTestRuns(id) {
  const { data } = await dataQualityClient.get(`/semantic-indicators/${id}/test-runs`);
  return data;
}

export async function getIndicatorTestRun(testRunId) {
  const { data } = await dataQualityClient.get(`/semantic-indicators/test-runs/${testRunId}`);
  return data;
}