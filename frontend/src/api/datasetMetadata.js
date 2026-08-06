import { dataQualityClient } from "./parsingJobs.js";

// UC-042 (Đăng ký siêu dữ liệu tập dữ liệu) dùng chung data-quality-service
// nên dùng lại `dataQualityClient` (baseURL "/api/data-quality") của
// UC-029/.../041 — không cần proxy dev mới.

export const SENSITIVITY_LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"];

/** Bước 3 "Tra cứu siêu dữ liệu tập dữ liệu" -- hệ thống hiển thị (danh sách). */
export async function listDatasetMetadata({ sensitivityLevel = null, owner = null } = {}) {
  const { data } = await dataQualityClient.get("/dataset-metadata", {
    params: {
      ...(sensitivityLevel ? { sensitivity_level: sensitivityLevel } : {}),
      ...(owner ? { owner } : {}),
    },
  });
  return data;
}

/** Bước 3 "Tra cứu siêu dữ liệu tập dữ liệu" -- hệ thống hiển thị (1 dataset). */
export async function getDatasetMetadata(datasetId) {
  const { data } = await dataQualityClient.get(`/dataset-metadata/${datasetId}`);
  return data;
}

export async function listDatasetMetadataVersions(datasetId) {
  const { data } = await dataQualityClient.get(`/dataset-metadata/${datasetId}/versions`);
  return data;
}

/** Bước 1 "Đăng ký siêu dữ liệu tập dữ liệu (chủ sở hữu, mô tả, mức nhạy cảm)". */
export async function registerDatasetMetadata({
  datasetId,
  owner,
  description = null,
  sensitivityLevel = "INTERNAL",
  note = null,
}) {
  const { data } = await dataQualityClient.post("/dataset-metadata", {
    dataset_id: datasetId,
    owner,
    ...(description ? { description } : {}),
    sensitivity_level: sensitivityLevel,
    ...(note ? { note } : {}),
  });
  return data;
}

/** Bước 2 "Cập nhật siêu dữ liệu" -- hệ thống lưu phiên bản mới. */
export async function updateDatasetMetadata(
  datasetId,
  { owner = null, description = null, clearDescription = false, sensitivityLevel = null, note = null },
) {
  const { data } = await dataQualityClient.put(`/dataset-metadata/${datasetId}`, {
    ...(owner ? { owner } : {}),
    ...(description ? { description } : {}),
    clear_description: clearDescription,
    ...(sensitivityLevel ? { sensitivity_level: sensitivityLevel } : {}),
    ...(note ? { note } : {}),
  });
  return data;
}