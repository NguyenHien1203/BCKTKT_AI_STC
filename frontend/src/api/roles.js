import { authIdentityClient } from "./orgUnits";

export async function listRoles() {
  const { data } = await authIdentityClient.get("/roles");
  return data;
}

export async function getRole(id) {
  const { data } = await authIdentityClient.get(`/roles/${id}`);
  return data;
}

export async function createRole(payload) {
  const { data } = await authIdentityClient.post("/roles", payload);
  return data;
}

export async function updateRole(id, payload) {
  const { data } = await authIdentityClient.patch(`/roles/${id}`, payload);
  return data;
}

export async function deleteRole(id) {
  await authIdentityClient.delete(`/roles/${id}`);
}