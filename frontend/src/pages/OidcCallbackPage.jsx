import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { createOidcSession, exchangeCodeForToken } from "../api/oidc.js";

const PKCE_VERIFIER_KEY = "oidc_code_verifier";
const PKCE_STATE_KEY = "oidc_state";
const OIDC_CONFIG_KEY = "oidc_config_cache";

export default function OidcCallbackPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const ranOnce = useRef(false);

  useEffect(() => {
    if (ranOnce.current) return; // React StrictMode gọi effect 2 lần ở dev — tránh đổi code 2 lần
    ranOnce.current = true;

    async function run() {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const state = params.get("state");
      const errorParam = params.get("error");

      const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
      const codeVerifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
      const configRaw = sessionStorage.getItem(OIDC_CONFIG_KEY);

      // Dọn dẹp ngay để không tái sử dụng nhầm cho lần đăng nhập sau.
      sessionStorage.removeItem(PKCE_VERIFIER_KEY);
      sessionStorage.removeItem(PKCE_STATE_KEY);
      sessionStorage.removeItem(OIDC_CONFIG_KEY);

      if (errorParam) {
        setError(`Keycloak từ chối đăng nhập: ${errorParam}`);
        return;
      }
      if (!code || !state || !expectedState || state !== expectedState || !codeVerifier || !configRaw) {
        setError("Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng thử đăng nhập lại.");
        return;
      }

      try {
        const config = JSON.parse(configRaw);
        const redirectUri = `${window.location.origin}/auth/callback`;

        const tokenSet = await exchangeCodeForToken({
          authBaseUrl: config.auth_base_url,
          realm: config.realm,
          clientId: config.client_id,
          code,
          redirectUri,
          codeVerifier,
        });

        const { token, user } = await createOidcSession(tokenSet.access_token);
        setSession(token, user, tokenSet.id_token);
        navigate("/", { replace: true });
      } catch {
        setError("Đăng nhập qua Keycloak thất bại. Vui lòng thử lại.");
      }
    }

    run();
  }, [navigate, setSession]);

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
      <div className="card" style={{ width: 380, padding: 32, textAlign: "center" }}>
        {error ? (
          <>
            <div className="alert alert-error" style={{ marginBottom: 16 }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
            <a href="/login" className="btn btn-primary" style={{ justifyContent: "center" }}>
              Quay lại trang đăng nhập
            </a>
          </>
        ) : (
          <div style={{ color: "var(--color-text-secondary)" }}>Đang hoàn tất đăng nhập...</div>
        )}
      </div>
    </div>
  );
}
