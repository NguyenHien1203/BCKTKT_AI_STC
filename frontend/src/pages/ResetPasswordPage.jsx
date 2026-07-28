import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2, KeyRound } from "lucide-react";
import { resetPassword } from "../api/password.js";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token) {
      setError("Thiếu token cấp lại mật khẩu. Vui lòng dùng đúng link trong email.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Mật khẩu mới phải có tối thiểu 8 ký tự.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Xác nhận mật khẩu mới không khớp.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await resetPassword(token, newPassword);
      setSuccess(res?.message || "Cấp lại mật khẩu thành công. Vui lòng đăng nhập lại.");
      setTimeout(() => navigate("/login"), 1800);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cấp lại mật khẩu thất bại");
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
            Đặt lại mật khẩu
          </div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            UC-13 — Đặt mật khẩu mới bằng link đã nhận qua email.
          </div>
        </div>

        {!token && (
          <div className="alert alert-error" style={{ marginBottom: 20 }}>
            <AlertCircle size={16} />
            <span>Không tìm thấy token trong đường dẫn. Vui lòng mở lại link từ email.</span>
          </div>
        )}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 20 }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="alert alert-success" style={{ marginBottom: 20 }}>
            <CheckCircle2 size={16} />
            <span>{success}</span>
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit}>
            <div className="field" style={{ marginBottom: 14 }}>
              <label htmlFor="new_password">Mật khẩu mới</label>
              <input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={8}
                autoFocus
                required
              />
            </div>
            <div className="field" style={{ marginBottom: 20 }}>
              <label htmlFor="confirm_password">Xác nhận mật khẩu mới</label>
              <input
                id="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center" }}
              disabled={submitting}
            >
              <KeyRound size={15} />
              {submitting ? "Đang xử lý..." : "Đặt lại mật khẩu"}
            </button>
          </form>
        )}

        <div style={{ marginTop: 18, textAlign: "center" }}>
          <Link
            to="/login"
            style={{ fontSize: 13, color: "var(--color-primary)", textDecoration: "none" }}
          >
            Quay lại đăng nhập
          </Link>
        </div>
      </div>
    </div>
  );
}