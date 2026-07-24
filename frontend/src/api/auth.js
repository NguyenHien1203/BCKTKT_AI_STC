import { authIdentityClient } from "./orgUnits";

export async function login(username, password) {
  const { data } = await authIdentityClient.post("/auth/login", { username, password });
  return data; // { token, user }
}

export async function logout(token) {
  await authIdentityClient.post(
    "/auth/logout",
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function fetchCurrentUser(token) {
  const { data } = await authIdentityClient.get("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}
