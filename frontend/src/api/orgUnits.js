import axios from "axios";

// Qua Vite dev proxy (xem vite.config.js) -> auth-identity-service (port 8001).
// Khi build production, đổi baseURL này thành URL của APISIX Gateway thật.
export const authIdentityClient = axios.create({
  baseURL: "/api/auth-identity",
});

export async function listOrgUnits(onlyActive = false) {
  const { data } = await authIdentityClient.get("/org-units", {
    params: { only_active: onlyActive },
  });
  return data;
}

export async function createOrgUnit(payload) {
  const { data } = await authIdentityClient.post("/org-units", payload);
  return data;
}

export async function renameOrgUnit(id, name) {
  const { data } = await authIdentityClient.patch(`/org-units/${id}/rename`, { name });
  return data;
}

export async function deactivateOrgUnit(id) {
  const { data } = await authIdentityClient.post(`/org-units/${id}/deactivate`);
  return data;
}

export async function activateOrgUnit(id) {
  const { data } = await authIdentityClient.post(`/org-units/${id}/activate`);
  return data;
}

export async function deleteOrgUnit(id) {
  await authIdentityClient.delete(`/org-units/${id}`);
}
