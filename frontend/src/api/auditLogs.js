import { authIdentityClient } from "./orgUnits";

export async function listAuditLogs({ account = "", timeFrom = "", timeTo = "" } = {}) {
  const params = {};
  if (account) params.account = account;
  if (timeFrom) params.time_from = timeFrom;
  if (timeTo) params.time_to = timeTo;
  const { data } = await authIdentityClient.get("/audit-logs", { params });
  return data;
}

export async function exportSecurityReport({ timeFrom = "", timeTo = "" } = {}) {
  const params = {};
  if (timeFrom) params.time_from = timeFrom;
  if (timeTo) params.time_to = timeTo;
  const response = await authIdentityClient.get("/audit-logs/export", {
    params,
    responseType: "blob",
  });
  return response.data;
}