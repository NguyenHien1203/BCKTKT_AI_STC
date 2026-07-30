import { createContext, useContext, useEffect, useState } from "react";
import { fetchCurrentUser, login as loginApi, logout as logoutApi } from "../api/auth";
import { buildEndSessionUrl, getOidcConfig } from "../api/oidc";

const AuthContext = createContext(null);

const STORAGE_KEY = "financial_dw_token";
// id_token của Keycloak (nếu đăng nhập qua SSO) — chỉ dùng để đăng xuất luôn
// khỏi phiên SSO (RP-Initiated Logout), không dùng để gọi API nội bộ.
const ID_TOKEN_KEY = "financial_dw_id_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [idToken, setIdToken] = useState(() => localStorage.getItem(ID_TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const current = await fetchCurrentUser(token);
        setUser(current);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    restoreSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(username, password) {
    const { token: newToken, user: newUser } = await loginApi(username, password);
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setUser(newUser);
  }

  // Dùng bởi luồng OIDC (Keycloak Authorization Code Flow + PKCE): sau khi
  // backend xác nhận access_token hợp lệ và trả về {token, user} nội bộ,
  // lưu session giống hệt luồng đăng nhập username/password cũ.
  // newIdToken (id_token của Keycloak) được lưu thêm để dùng lúc đăng xuất
  // (RP-Initiated Logout) — không dùng cho việc gọi API.
  function setSession(newToken, newUser, newIdToken) {
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setUser(newUser);
    if (newIdToken) {
      localStorage.setItem(ID_TOKEN_KEY, newIdToken);
      setIdToken(newIdToken);
    }
  }

  async function logout() {
    const currentIdToken = idToken;

    if (token) {
      try {
        await logoutApi(token);
      } catch {
        // phiên có thể đã hết hạn ở server — vẫn xoá phía client
      }
    }
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ID_TOKEN_KEY);
    setToken(null);
    setUser(null);
    setIdToken(null);

    // Nếu đăng nhập qua Keycloak SSO: chỉ xoá session nội bộ là CHƯA đủ.
    // Keycloak vẫn giữ cookie phiên SSO trên trình duyệt, nên lần đăng nhập
    // kế tiếp sẽ tự động vào thẳng trang chủ mà không hỏi lại mật khẩu. Phải
    // điều hướng sang endpoint "end_session" của Keycloak (RP-Initiated
    // Logout) để kết thúc luôn phiên đó.
    if (currentIdToken) {
      try {
        const cfg = await getOidcConfig();
        if (cfg?.enabled) {
          const url = buildEndSessionUrl({
            authBaseUrl: cfg.auth_base_url,
            realm: cfg.realm,
            idTokenHint: currentIdToken,
            postLogoutRedirectUri: `${window.location.origin}/login`,
          });
          window.location.href = url;
          return; // trang sẽ điều hướng ra khỏi app, không cần làm gì thêm
        }
      } catch {
        // không lấy được cấu hình OIDC — vẫn coi như đã đăng xuất phía app,
        // chỉ là phiên SSO trên Keycloak có thể còn tồn tại.
      }
    }
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, setSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải dùng trong AuthProvider");
  return ctx;
}
