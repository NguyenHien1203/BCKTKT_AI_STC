import { authIdentityClient } from "./orgUnits";

// UC-13: Đổi mật khẩu / Cấp lại mật khẩu

export async function changePassword(token, oldPassword, newPassword) {
  const { data } = await authIdentityClient.post(
    "/auth/change-password",
    { old_password: oldPassword, new_password: newPassword },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return data; // MessageResponse
}

export async function forgotPassword(username) {
  const { data } = await authIdentityClient.post("/auth/forgot-password", { username });
  return data; // MessageResponse
}

export async function resetPassword(token, newPassword) {
  const { data } = await authIdentityClient.post("/auth/reset-password", {
    token,
    new_password: newPassword,
  });
  return data; // MessageResponse
}

export async function adminResetPassword(userId) {
  const { data } = await authIdentityClient.post(`/users/${userId}/reset-password`);
  return data; // MessageResponse
}