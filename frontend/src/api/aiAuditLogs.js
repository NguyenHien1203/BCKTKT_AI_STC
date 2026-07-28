import { authIdentityClient } from "./orgUnits";

export async function listAiAuditLogs({ userId = "", timeFrom = "", timeTo = "" } = {}) {
  const params = {};
  if (userId) params.user_id = userId;
  if (timeFrom) params.time_from = timeFrom;
  if (timeTo) params.time_to = timeTo;
  const { data } = await authIdentityClient.get("/ai-audit-logs", { params });
  return data;
}

export async function getAiAuditLogByTraceId(traceId) {
  const { data } = await authIdentityClient.get(`/ai-audit-logs/${encodeURIComponent(traceId)}`);
  return data;
}

export async function exportAiAuditReport({ period = "WEEK", timeFrom = "", timeTo = "" } = {}) {
  const params = { period };
  if (timeFrom) params.time_from = timeFrom;
  if (timeTo) params.time_to = timeTo;
  const response = await authIdentityClient.get("/ai-audit-logs/export", {
    params,
    responseType: "blob",
  });
  return response.data;
}