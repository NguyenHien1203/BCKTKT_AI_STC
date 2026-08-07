import { dataQualityClient } from "./parsingJobs.js";

// UC-045 (Truy vết nguồn gốc bản ghi) dùng chung data-quality-service
// với UC-029/.../044 nên dùng lại `dataQualityClient`
// (baseURL "/api/data-quality"). Danh sách bản ghi curated để "chọn"
// (bước 1) dùng lại `listDmRecords` của UC-041 (`api/curatedPublish.js`).

export const LINEAGE_STEPS = ["RAW", "PARSING", "MAPPING", "QUALITY", "PUBLISH"];

export const LINEAGE_STEP_LABELS = {
  RAW: "Dữ liệu thô",
  PARSING: "Phân tích",
  MAPPING: "Ánh xạ",
  QUALITY: "Chất lượng",
  PUBLISH: "Công bố",
};

/** Bước 1 "Chọn bản ghi curated": xem lại thông tin 1 bản ghi cụ thể. */
export async function getCuratedRecord(curatedDmRecordId) {
  const { data } = await dataQualityClient.get(
    `/record-lineage/curated-records/${curatedDmRecordId}`
  );
  return data;
}

/**
 * Bước 2 "Xem nguồn gốc dữ liệu qua các bước (thô -> phân tích -> ánh
 * xạ -> chất lượng -> công bố)": hệ thống hiển thị chuỗi.
 */
export async function getLineageChain(curatedDmRecordId) {
  const { data } = await dataQualityClient.get(
    `/record-lineage/curated-records/${curatedDmRecordId}/chain`
  );
  return data;
}

/**
 * Bước 3 "Xem chi tiết từng bước": hệ thống hiển thị dữ liệu vào/ra +
 * phép biến đổi của 1 bước cụ thể (RAW/PARSING/MAPPING/QUALITY/PUBLISH).
 */
export async function getLineageStepDetail(curatedDmRecordId, step) {
  const { data } = await dataQualityClient.get(
    `/record-lineage/curated-records/${curatedDmRecordId}/steps/${step}`
  );
  return data;
}