import { dataQualityClient } from "./parsingJobs.js";

// UC-041 (Công bố vào kho chuẩn hoá + batch_summary) dùng chung
// data-quality-service với UC-029/.../040 nên dùng lại `dataQualityClient`
// (baseURL "/api/data-quality").

/**
 * Mô phỏng nhận sự kiện "curated.publish.requested" (phát bởi UC-039 bước 3a
 * khi đạt ngưỡng chất lượng, hoặc UC-040 khi Phụ trách Dữ liệu chọn FIX 1
 * ngoại lệ chất lượng) -- kích hoạt trọn luồng UC-041: bước 1 chèn/cập nhật
 * vào dm_* -> bước 2 đặt publish_status=approved -> bước 3 tạo batch_summary
 * + cập nhật độ mới dữ liệu -> bước 4 phát sự kiện curated.published.
 */
export async function runCuratedPublish({
  qualityCheckJobId,
  datasetId = null,
  mappingJobId = null,
  recordCount = null,
  source = "uc039_quality_check",
}) {
  const { data } = await dataQualityClient.post("/curated-publish/jobs", {
    quality_check_job_id: qualityCheckJobId,
    ...(datasetId !== null ? { dataset_id: datasetId } : {}),
    ...(mappingJobId !== null ? { mapping_job_id: mappingJobId } : {}),
    ...(recordCount !== null ? { record_count: recordCount } : {}),
    source,
  });
  return data;
}

export async function listCuratedPublishJobs({
  datasetId = null,
  qualityCheckJobId = null,
  status = null,
} = {}) {
  const { data } = await dataQualityClient.get("/curated-publish/jobs", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(qualityCheckJobId !== null ? { quality_check_job_id: qualityCheckJobId } : {}),
      ...(status ? { status } : {}),
    },
  });
  return data;
}

export async function getCuratedPublishJob(id) {
  const { data } = await dataQualityClient.get(`/curated-publish/jobs/${id}`);
  return data;
}

/** Bước 1 "Chèn/Cập nhật vào dm_*": các bản ghi đã chèn/cập nhật trong 1 lượt công bố. */
export async function listCuratedPublishJobDmRecords(id) {
  const { data } = await dataQualityClient.get(`/curated-publish/jobs/${id}/dm-records`);
  return data;
}

/** Xem toàn bộ kho chuẩn hoá (dm_*) -- lọc theo tập dữ liệu/publish_status. */
export async function listDmRecords({ datasetId = null, publishStatus = null } = {}) {
  const { data } = await dataQualityClient.get("/curated-publish/dm-records", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(publishStatus ? { publish_status: publishStatus } : {}),
    },
  });
  return data;
}

/** Bước 3 "Tạo batch_summary": lịch sử các lượt công bố. */
export async function listBatchSummaries({ datasetId = null, qualityCheckJobId = null } = {}) {
  const { data } = await dataQualityClient.get("/curated-publish/batch-summaries", {
    params: {
      ...(datasetId !== null ? { dataset_id: datasetId } : {}),
      ...(qualityCheckJobId !== null ? { quality_check_job_id: qualityCheckJobId } : {}),
    },
  });
  return data;
}

/** Bước 3 "cập nhật độ mới dữ liệu" -- độ mới của 1 tập dữ liệu cụ thể. */
export async function getDatasetFreshness(datasetId) {
  const { data } = await dataQualityClient.get(`/curated-publish/dataset-freshness/${datasetId}`);
  return data;
}

/** Bước 3 "cập nhật độ mới dữ liệu" -- toàn bộ tập dữ liệu đã công bố. */
export async function listDatasetFreshness() {
  const { data } = await dataQualityClient.get("/curated-publish/dataset-freshness");
  return data;
}