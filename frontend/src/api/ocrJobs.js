import { dataQualityClient } from "./parsingJobs.js";

// UC-030 — Phân tích PDF/bản quét + OCR. Dùng chung dataQualityClient
// (baseURL /api/data-quality) với parsingJobs.js (UC-029), cùng service
// data-quality-service (port 8003).

export async function receiveOcrRequested({
  rawObjectKey,
  vanBanIntakeId = null,
  dataSourceId = null,
  soKyHieu = null,
  engine = null,
}) {
  const { data } = await dataQualityClient.post("/ocr-jobs", {
    raw_object_key: rawObjectKey,
    ...(vanBanIntakeId ? { van_ban_intake_id: vanBanIntakeId } : {}),
    ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
    ...(soKyHieu ? { so_ky_hieu: soKyHieu } : {}),
    ...(engine ? { engine } : {}),
  });
  return data;
}

export async function listOcrJobs({ dataSourceId = null, status = null, vanBanIntakeId = null } = {}) {
  const { data } = await dataQualityClient.get("/ocr-jobs", {
    params: {
      ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
      ...(status ? { status } : {}),
      ...(vanBanIntakeId ? { van_ban_intake_id: vanBanIntakeId } : {}),
    },
  });
  return data;
}

export async function getOcrJob(id) {
  const { data } = await dataQualityClient.get(`/ocr-jobs/${id}`);
  return data;
}

export async function listOcrTables(id) {
  const { data } = await dataQualityClient.get(`/ocr-jobs/${id}/tables`);
  return data;
}