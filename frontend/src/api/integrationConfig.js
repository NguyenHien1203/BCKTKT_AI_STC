import { authIdentityClient } from "./orgUnits";

export async function listIntegrationEndpoints() {
  const { data } = await authIdentityClient.get("/integration-config");
  return data;
}

export async function getKeycloakConfig() {
  const { data } = await authIdentityClient.get("/integration-config/keycloak");
  return data;
}

export async function configureKeycloak(payload) {
  const { data } = await authIdentityClient.put("/integration-config/keycloak", payload);
  return data;
}

export async function recheckKeycloak() {
  const { data } = await authIdentityClient.post("/integration-config/keycloak/recheck");
  return data;
}

export async function getLgspConfig() {
  const { data } = await authIdentityClient.get("/integration-config/lgsp");
  return data;
}

export async function configureLgsp(payload) {
  const { data } = await authIdentityClient.put("/integration-config/lgsp", payload);
  return data;
}

export async function recheckLgsp() {
  const { data } = await authIdentityClient.post("/integration-config/lgsp/recheck");
  return data;
}