import { authIdentityClient } from "./orgUnits";

export async function listUsers(params = {}) {
  const { data } = await authIdentityClient.get("/users", { params });
  return data;
}

export async function createUser(payload) {
  const { data } = await authIdentityClient.post("/users", payload);
  return data;
}

export async function updateUserProfile(id, payload) {
  const { data } = await authIdentityClient.patch(`/users/${id}/profile`, payload);
  return data;
}

export async function reassignUserOrgUnit(id, orgUnitId) {
  const { data } = await authIdentityClient.patch(`/users/${id}/org-unit`, {
    org_unit_id: orgUnitId,
  });
  return data;
}

export async function deactivateUser(id) {
  const { data } = await authIdentityClient.post(`/users/${id}/deactivate`);
  return data;
}

export async function activateUser(id) {
  const { data } = await authIdentityClient.post(`/users/${id}/activate`);
  return data;
}

export async function deleteUser(id) {
  await authIdentityClient.delete(`/users/${id}`);
}
