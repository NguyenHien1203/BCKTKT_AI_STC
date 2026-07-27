import { authIdentityClient } from "./orgUnits";

export async function getSystemConfig() {
  const { data } = await authIdentityClient.get("/system-config");
  return data;
}

export async function updateSystemConfig(payload) {
  const { data } = await authIdentityClient.patch("/system-config", payload);
  return data;
}