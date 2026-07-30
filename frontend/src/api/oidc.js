import { authIdentityClient } from "./orgUnits";

// GET /auth/oidc/config -> { enabled, auth_base_url, realm, client_id }
export async function getOidcConfig() {
  const { data } = await authIdentityClient.get("/auth/oidc/config");
  return data;
}

// Sau khi frontend đổi `code` lấy access_token trực tiếp với Keycloak (PKCE,
// public client — không cần client_secret), gửi access_token cho backend để
// backend map sang user nội bộ + tạo session (giống hệt response của /auth/login cũ).
export async function createOidcSession(accessToken) {
  const { data } = await authIdentityClient.post("/auth/oidc/session", {
    access_token: accessToken,
  });
  return data; // { token, user }
}

// --- Tiện ích PKCE (Authorization Code Flow + PKCE, RFC 7636) ---

function base64UrlEncode(bytes) {
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function generateRandomString(length = 64) {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return base64UrlEncode(array).slice(0, length);
}

export async function generateCodeChallenge(codeVerifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return base64UrlEncode(new Uint8Array(digest));
}

// Xây URL "authorize" của Keycloak để redirect trình duyệt sang trang đăng
// nhập thật của Keycloak (KHÔNG bao giờ đăng nhập trên form của app nữa).
export function buildAuthorizeUrl({ authBaseUrl, realm, clientId, redirectUri, state, codeChallenge }) {
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid profile email",
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });
  return `${authBaseUrl}/realms/${realm}/protocol/openid-connect/auth?${params.toString()}`;
}

// Đổi authorization `code` lấy access_token TRỰC TIẾP với Keycloak (public
// client + PKCE => không cần client_secret ở frontend).
export async function exchangeCodeForToken({ authBaseUrl, realm, clientId, code, redirectUri, codeVerifier }) {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: clientId,
    code,
    redirect_uri: redirectUri,
    code_verifier: codeVerifier,
  });
  const resp = await fetch(`${authBaseUrl}/realms/${realm}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    throw new Error("Đổi mã xác thực (code) với Keycloak thất bại");
  }
  return resp.json(); // { access_token, id_token, refresh_token, ... }
}

// Xây URL "end_session" (RP-Initiated Logout, OIDC) để đăng xuất luôn khỏi
// phiên SSO của Keycloak — không chỉ session nội bộ của app. Nếu không gọi
// bước này, Keycloak vẫn còn cookie phiên đăng nhập của trình duyệt, nên lần
// "đăng nhập lại" kế tiếp sẽ tự động vào thẳng trang chủ mà không hỏi lại
// mật khẩu (vì Keycloak tự cấp code mới mà không hiển thị form đăng nhập).
export function buildEndSessionUrl({ authBaseUrl, realm, idTokenHint, postLogoutRedirectUri }) {
  const params = new URLSearchParams({
    post_logout_redirect_uri: postLogoutRedirectUri,
  });
  if (idTokenHint) params.set("id_token_hint", idTokenHint);
  return `${authBaseUrl}/realms/${realm}/protocol/openid-connect/logout?${params.toString()}`;
}
