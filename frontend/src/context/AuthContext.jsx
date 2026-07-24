import { createContext, useContext, useEffect, useState } from "react";
import { fetchCurrentUser, login as loginApi, logout as logoutApi } from "../api/auth";

const AuthContext = createContext(null);

const STORAGE_KEY = "financial_dw_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
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

  async function logout() {
    if (token) {
      try {
        await logoutApi(token);
      } catch {
        // phiên có thể đã hết hạn ở server — vẫn xoá phía client
      }
    }
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải dùng trong AuthProvider");
  return ctx;
}
