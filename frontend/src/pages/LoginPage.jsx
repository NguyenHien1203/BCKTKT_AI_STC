import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import {
  buildAuthorizeUrl,
  generateCodeChallenge,
  generateRandomString,
  getOidcConfig,
} from "../api/oidc.js";

const PKCE_VERIFIER_KEY = "oidc_code_verifier";
const PKCE_STATE_KEY = "oidc_state";
const OIDC_CONFIG_KEY = "oidc_config_cache";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // null = đang tải cấu hình; false = dùng form nội bộ; object = SSO Keycloak bật
  const [oidcConfig, setOidcConfig] = useState(null);
  const [oidcLoading, setOidcLoading] = useState(false);

  useEffect(() => {
    getOidcConfig()
      .then((cfg) => setOidcConfig(cfg.enabled ? cfg : false))
      .catch(() => setOidcConfig(false));
  }, []);

  // Bỏ hẳn trang "Kho Dữ Liệu Tài Chính" với nút bấm — khi bật SSO Keycloak,
  // vừa xác định được cấu hình xong là điều hướng thẳng sang Keycloak luôn,
  // không cần người dùng bấm nút "Đăng nhập qua Keycloak" nữa.
  useEffect(() => {
    if (oidcConfig) {
      handleLoginWithKeycloak();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oidcConfig]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Đăng nhập thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Điều hướng trình duyệt sang trang đăng nhập THẬT của Keycloak.
  // App không bao giờ thấy mật khẩu người dùng (Authorization Code Flow + PKCE).
  async function handleLoginWithKeycloak() {
    if (!oidcConfig) return;
    setOidcLoading(true);
    setError(null);
    try {
      const codeVerifier = generateRandomString(64);
      const state = generateRandomString(32);
      const codeChallenge = await generateCodeChallenge(codeVerifier);

      sessionStorage.setItem(PKCE_VERIFIER_KEY, codeVerifier);
      sessionStorage.setItem(PKCE_STATE_KEY, state);
      sessionStorage.setItem(OIDC_CONFIG_KEY, JSON.stringify(oidcConfig));

      const redirectUri = `${window.location.origin}/auth/callback`;
      const url = buildAuthorizeUrl({
        authBaseUrl: oidcConfig.auth_base_url,
        realm: oidcConfig.realm,
        clientId: oidcConfig.client_id,
        redirectUri,
        state,
        codeChallenge,
      });
      window.location.href = url;
    } catch {
      setError("Không thể điều hướng sang Keycloak. Vui lòng thử lại.");
      setOidcLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-bg)",
      }}
    >
      <div className="card" style={{ width: 380, padding: 32 }}>
        {/* Khi SSO Keycloak bật: không hiển thị trang đăng nhập riêng của app
            nữa — effect ở trên tự điều hướng thẳng sang Keycloak ngay khi có
            cấu hình. Card ở đây chỉ còn dùng cho lỗi/đang tải, hoặc cho
            trường hợp AUTH_PROVIDER=local (form nội bộ, dùng cho dev/test). */}
        {oidcConfig === false && (
          <div style={{ marginBottom: 24, textAlign: "center" }}>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>
              Kho Dữ Liệu Tài Chính
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
              Tỉnh Hưng Yên — Đăng nhập hệ thống
            </div>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {(oidcConfig === null || (oidcConfig && !error)) && (
          <div style={{ textAlign: "center", padding: "24px 0", color: "var(--color-text-secondary)" }}>
            {oidcConfig === null
              ? "Đang tải cấu hình đăng nhập..."
              : "Đang chuyển hướng sang hệ thống đăng nhập Keycloak..."}
          </div>
        )}

        {oidcConfig && error && (
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center" }}
            disabled={oidcLoading}
            onClick={handleLoginWithKeycloak}
          >
            <ShieldCheck size={15} />
            {oidcLoading ? "Đang chuyển hướng..." : "Thử lại đăng nhập qua Keycloak"}
          </button>
        )}

        {oidcConfig === false && (
          <>
            <form onSubmit={handleSubmit}>
              <div className="field" style={{ marginBottom: 14 }}>
                <label htmlFor="username">Tên đăng nhập</label>
                <input
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <div className="field" style={{ marginBottom: 20 }}>
                <label htmlFor="password">Mật khẩu</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: "100%", justifyContent: "center" }}
                disabled={submitting}
              >
                <LogIn size={15} />
                {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
              </button>
            </form>

            <div style={{ marginTop: 16, textAlign: "center" }}>
              <Link
                to="/forgot-password"
                style={{ fontSize: 13, color: "var(--color-primary)", textDecoration: "none" }}
              >
                Quên mật khẩu?
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
