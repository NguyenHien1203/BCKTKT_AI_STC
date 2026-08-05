import { dataQualityClient } from "./parsingJobs.js";

// UC-039 (Chạy kiểm tra chất lượng dữ liệu) dùng chung data-quality-service
// với UC-029/.../038 nên dùng lại `dataQualityClient` (baseURL "/api/data-quality").

/**
 * Mô phỏng nhận sự kiện "mapping.completed" (phát bởi UC-031 sau khi ánh xạ
 * trường sang dạng chuẩn xong) -- kích hoạt trọn luồng UC-039: bước 1 tra cứu
 * quy tắc chất lượng -> bước 2 chạy quy tắc + tính điểm -> bước 3a/3b công bố
 * vào kho chuẩn hoá hoặc đẩy vào hàng đợi ngoại lệ.
 */
export async function runQualityCheck({ mappingJobId, datasetId = null }) {
  const { data } = await dataQualityClient.post("/quality-checks", {
    mapping_job_id: mappingJobId,
    ...(datasetId !== null ? { dataset_id: datasetId } : {}),
  });
  return data;
}

export async function listQualityChecks({ datasetId = null, mappingJobId = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/quality-checks", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(mappingJobId !== null ? { mapping_job_id: mappingJobId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getQualityCheck(id) {
  const { data } = await dataQualityClient.get(`/quality-checks/${id}`);
  return data;
}

/** Bước 2 "Chạy quy tắc": kết quả từng quy tắc áp dụng, phục vụ audit. */
export async function listQualityCheckRuleResults(id) {
  const { data } = await dataQualityClient.get(`/quality-checks/${id}/rule-results`);
  return data;
}

/** Bước 3a "Đạt ngưỡng -> công bố": bản ghi đã đẩy vào kho chuẩn hoá. */
export async function listQualityCheckPublishedRecords(id) {
  const { data } = await dataQualityClient.get(`/quality-checks/${id}/published-records`);
  return data;
}

/** Bước 3b "Dưới ngưỡng -> hàng đợi ngoại lệ": các dòng đẩy cho Phụ trách Dữ liệu. */
export async function listQualityCheckExceptionItems(id) {
  const { data } = await dataQualityClient.get(`/quality-checks/${id}/exception-items`);
  return data;
}

/**
 * UC-040 bước 1 "Xem hàng đợi ngoại lệ" -- toàn bộ hàng đợi (không giới hạn
 * theo 1 lượt kiểm tra cụ thể). Hiển thị ở đây để đối chiếu nhanh sau khi
 * chạy UC-039, việc xử lý ngoại lệ đầy đủ thuộc UC-040.
 */
export async function listQualityExceptionQueue({ datasetId = null, status = null } = {}) {
  const { data } = await dataQualityClient.get("/quality-checks/exception-queue/list", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}