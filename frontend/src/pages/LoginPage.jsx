import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, LogIn } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

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
        <div style={{ marginBottom: 24, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>
            Kho Dữ Liệu Tài Chính
          </div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            Tỉnh Hưng Yên — Đăng nhập hệ thống
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

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
      </div>
    </div>
  );
}
