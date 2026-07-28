import { authIdentityClient } from "./orgUnits";

export async function listGuideDocuments({ onlyActive = false, category = "" } = {}) {
  const { data } = await authIdentityClient.get("/guide-documents", {
    params: {
      only_active: onlyActive,
      ...(category ? { category } : {}),
    },
  });
  return data;
}

export async function getGuideDocument(id) {
  const { data } = await authIdentityClient.get(`/guide-documents/${id}`);
  return data;
}

export async function addGuideDocument({ title, description, category, uploadedBy, file }) {
  const form = new FormData();
  form.append("title", title);
  form.append("description", description || "");
  form.append("category", category || "");
  form.append("uploaded_by", uploadedBy);
  form.append("file", file);
  const { data } = await authIdentityClient.post("/guide-documents", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function updateGuideDocument(id, { title, description, category, uploadedBy, file }) {
  const form = new FormData();
  if (title !== undefined && title !== null) form.append("title", title);
  if (description !== undefined && description !== null) form.append("description", description);
  if (category !== undefined && category !== null) form.append("category", category);
  form.append("uploaded_by", uploadedBy || "");
  if (file) form.append("file", file);
  const { data } = await authIdentityClient.put(`/guide-documents/${id}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function updateGuideDocumentMeta(id, payload) {
  const { data } = await authIdentityClient.patch(`/guide-documents/${id}/meta`, payload);
  return data;
}

export async function deleteGuideDocument(id) {
  const { data } = await authIdentityClient.delete(`/guide-documents/${id}`);
  return data;
}

export async function restoreGuideDocument(id) {
  const { data } = await authIdentityClient.post(`/guide-documents/${id}/restore`);
  return data;
}

export async function listGuideDocumentVersions(id) {
  const { data } = await authIdentityClient.get(`/guide-documents/${id}/versions`);
  return data;
}

export function guideDocumentDownloadUrl(id, version) {
  const base = `${authIdentityClient.defaults.baseURL}/guide-documents/${id}/download`;
  return version ? `${base}?version=${version}` : base;
}

export async function downloadGuideDocument(id, version) {
  const { data, headers } = await authIdentityClient.get(`/guide-documents/${id}/download`, {
    params: version ? { version } : {},
    responseType: "blob",
  });
  return { blob: data, contentType: headers["content-type"] };
}