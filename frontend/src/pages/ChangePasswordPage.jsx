import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, KeyRound } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { changePassword } from "../api/password.js";

const EMPTY_FORM = { old_password: "", new_password: "", confirm_password: "" };

export default function ChangePasswordPage() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (form.new_password.length < 8) {
      setError("Mật khẩu mới phải có tối thiểu 8 ký tự.");
      return;
    }
    if (form.new_password !== form.confirm_password) {
      setError("Xác nhận mật khẩu mới không khớp.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await changePassword(token, form.old_password, form.new_password);
      setSuccess(res?.message || "Đổi mật khẩu thành công. Vui lòng đăng nhập lại.");
      setForm(EMPTY_FORM);
      // Sau khi đổi mật khẩu, phiên hiện tại nên đăng xuất để đăng nhập lại
      // bằng mật khẩu mới cho an toàn.
      setTimeout(async () => {
        await logout();
        navigate("/login");
      }, 1800);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Đổi mật khẩu thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Đổi mật khẩu"
      subtitle="UC-13 — Tự đổi mật khẩu tài khoản đang đăng nhập."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{success}</span>
        </div>
      )}

      <div className="card" style={{ maxWidth: 480 }}>
        <div className="card-header">
          <h2>Thông tin mật khẩu</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="field" style={{ marginBottom: 14 }}>
              <label htmlFor="old_password">Mật khẩu hiện tại</label>
              <input
                id="old_password"
                type="password"
                value={form.old_password}
                onChange={(e) => setForm({ ...form, old_password: e.target.value })}
                autoFocus
                required
              />
            </div>
            <div className="field" style={{ marginBottom: 14 }}>
              <label htmlFor="new_password">Mật khẩu mới</label>
              <input
                id="new_password"
                type="password"
                value={form.new_password}
                onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                minLength={8}
                required
              />
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Tối thiểu 8 ký tự.
              </span>
            </div>
            <div className="field" style={{ marginBottom: 20 }}>
              <label htmlFor="confirm_password">Xác nhận mật khẩu mới</label>
              <input
                id="confirm_password"
                type="password"
                value={form.confirm_password}
                onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                minLength={8}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <KeyRound size={15} />
              {submitting ? "Đang xử lý..." : "Đổi mật khẩu"}
            </button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}