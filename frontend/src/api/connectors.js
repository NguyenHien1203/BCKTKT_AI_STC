import { ingestionClient } from "./dataSources.js";

// Dùng chung ingestionClient (baseURL "/api/ingestion") với dataSources.js
// vì cùng thuộc ingestion-service.

export async function listConnectors({ onlyActive = false, connectorType = null } = {}) {
  const { data } = await ingestionClient.get("/connectors", {
    params: {
      only_active: onlyActive,
      ...(connectorType ? { connector_type: connectorType } : {}),
    },
  });
  return data;
}

export async function getConnector(id) {
  const { data } = await ingestionClient.get(`/connectors/${id}`);
  return data;
}

export async function registerConnector(payload) {
  const { data } = await ingestionClient.post("/connectors", payload);
  return data;
}

export async function updateConnectorVersion(id, version) {
  const { data } = await ingestionClient.patch(`/connectors/${id}/version`, { version });
  return data;
}

export async function deactivateConnector(id) {
  const { data } = await ingestionClient.post(`/connectors/${id}/deactivate`);
  return data;
}

export async function activateConnector(id) {
  const { data } = await ingestionClient.post(`/connectors/${id}/activate`);
  return data;
}