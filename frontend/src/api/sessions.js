import { authIdentityClient } from "./orgUnits";

// UC-14: Quản lý phiên đăng nhập

export async function listSessions({ userId, onlyActive = true } = {}) {
  const { data } = await authIdentityClient.get("/sessions", {
    params: {
      user_id: userId ?? undefined,
      only_active: onlyActive,
    },
  });
  return data;
}

export async function listSessionsForUser(userId, onlyActive = true) {
  const { data } = await authIdentityClient.get(`/users/${userId}/sessions`, {
    params: { only_active: onlyActive },
  });
  return data;
}

export async function revokeSession(sessionId) {
  await authIdentityClient.delete(`/sessions/${sessionId}`);
}