import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, MailCheck, ShieldCheck } from "lucide-react";
import { forgotPassword } from "../api/password.js";
import { getOidcConfig } from "../api/oidc.js";

export default function ForgotPasswordPage() {
  const [username, setUsername] = useState("");
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // null = đang tải; false = flow "quên mật khẩu" nội bộ (AUTH_PROVIDER=local);
  // object = SSO Keycloak bật -> trang này không dùng nữa, "Quên mật khẩu" nằm
  // ngay trên form đăng nhập Keycloak.
  const [oidcConfig, setOidcConfig] = useState(null);

  useEffect(() => {
    getOidcConfig()
      .then((cfg) => setOidcConfig(cfg.enabled ? cfg : false))
      .catch(() => setOidcConfig(false));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await forgotPassword(username);
      // Backend luôn trả về thông điệp thành công chung (không tiết lộ
      // tài khoản có tồn tại hay không) để tránh dò quét tài khoản.
      setSuccess(
        res?.message || "Nếu tài khoản tồn tại, hệ thống đã gửi link cấp lại mật khẩu qua email."
      );
    } catch {
      // Theo thiết kế backend, endpoint này không trả lỗi khi tài khoản
      // không tồn tại — vẫn hiển thị thông điệp trung lập nếu có sự cố khác.
      setSuccess("Nếu tài khoản tồn tại, hệ thống đã gửi link cấp lại mật khẩu qua email.");
    } finally {
      setSubmitting(false);
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
      <div className="card" style={{ width: 400, padding: 32 }}>
        <div style={{ marginBottom: 24, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>
            Quên mật khẩu
          </div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            UC-13 — Nhập tên đăng nhập để nhận link cấp lại mật khẩu qua email.
          </div>
        </div>

        {oidcConfig === null && (
          <div style={{ textAlign: "center", padding: "12px 0", color: "var(--color-text-secondary)" }}>
            Đang tải cấu hình đăng nhập...
          </div>
        )}

        {oidcConfig && (
          <div className="alert alert-info" style={{ marginBottom: 20 }}>
            <ShieldCheck size={16} />
            <span>
              Hệ thống đang đăng nhập qua SSO Keycloak. Vui lòng dùng chức năng "Quên mật
              khẩu" ngay tại trang đăng nhập Keycloak thay vì trang này.
            </span>
          </div>
        )}

        {oidcConfig === false && success && (
          <div className="alert alert-success" style={{ marginBottom: 20 }}>
            <CheckCircle2 size={16} />
            <span>{success}</span>
          </div>
        )}
        {oidcConfig === false && !success && (
          <form onSubmit={handleSubmit}>
            <div className="field" style={{ marginBottom: 20 }}>
              <label htmlFor="username">Tên đăng nhập</label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center" }}
              disabled={submitting}
            >
              <MailCheck size={15} />
              {submitting ? "Đang gửi..." : "Gửi yêu cầu cấp lại mật khẩu"}
            </button>
          </form>
        )}

        <div style={{ marginTop: 18, textAlign: "center" }}>
          <Link
            to="/login"
            style={{
              fontSize: 13,
              color: "var(--color-primary)",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              textDecoration: "none",
            }}
          >
            <ArrowLeft size={14} />
            Quay lại đăng nhập
          </Link>
        </div>
      </div>
    </div>
  );
}