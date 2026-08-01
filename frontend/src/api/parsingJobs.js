import axios from "axios";

// Qua Vite dev proxy (xem vite.config.js) -> data-quality-service (port 8003).
// Khi build production, đổi baseURL này thành URL của APISIX Gateway thật.
export const dataQualityClient = axios.create({
  baseURL: "/api/data-quality",
});

export async function receiveParsingRequested({
  datasetId,
  rawObjectKey,
  schemaFields,
  sourceFormat = null,
  fieldMapping = {},
  ingestionRunId = null,
  dataSourceId = null,
}) {
  const { data } = await dataQualityClient.post("/parsing-jobs", {
    dataset_id: datasetId,
    raw_object_key: rawObjectKey,
    schema_fields: schemaFields,
    ...(sourceFormat ? { source_format: sourceFormat } : {}),
    field_mapping: fieldMapping,
    ...(ingestionRunId ? { ingestion_run_id: ingestionRunId } : {}),
    ...(dataSourceId ? { data_source_id: dataSourceId } : {}),
  });
  return data;
}

export async function listParsingJobs({ datasetId = null, status = null, ingestionRunId = null } = {}) {
  const { data } = await dataQualityClient.get("/parsing-jobs", {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...(status ? { status } : {}),
      ...(ingestionRunId ? { ingestion_run_id: ingestionRunId } : {}),
    },
  });
  return data;
}

export async function getParsingJob(id) {
  const { data } = await dataQualityClient.get(`/parsing-jobs/${id}`);
  return data;
}

export async function listParsingRowErrors(id) {
  const { data } = await dataQualityClient.get(`/parsing-jobs/${id}/row-errors`);
  return data;
}

export async function listParsedRecords(id) {
  const { data } = await dataQualityClient.get(`/parsing-jobs/${id}/parsed-records`);
  return data;
}