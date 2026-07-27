import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Save } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { getSystemConfig, updateSystemConfig } from "../api/systemConfig.js";

const EMPTY_FORM = {
  request_timeout_seconds: "",
  max_upload_size_mb: "",
  default_language: "vi",
};

export default function SystemConfigPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);

  async function reload() {
    setLoading(true);
    try {
      const data = await getSystemConfig();
      setForm({
        request_timeout_seconds: String(data.request_timeout_seconds),
        max_upload_size_mb: String(data.max_upload_size_mb),
        default_language: data.default_language,
      });
      setUpdatedAt(data.updated_at);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setSuccess(null);
    try {
      const data = await updateSystemConfig({
        request_timeout_seconds: Number(form.request_timeout_seconds),
        max_upload_size_mb: Number(form.max_upload_size_mb),
        default_language: form.default_language,
      });
      setUpdatedAt(data.updated_at);
      setError(null);
      setSuccess("Đã lưu và áp dụng cấu hình mới (nạp lại nóng).");
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppLayout
      title="Cấu hình hệ thống chung"
      subtitle="UC-06 — Xem/sửa thời gian chờ, dung lượng tải lên tối đa, ngôn ngữ mặc định. Áp dụng ngay, không cần khởi động lại."
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

      <div className="card">
        <div className="card-header">
          <h2>Cấu hình chung</h2>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="request_timeout_seconds">Thời gian chờ (giây)</label>
                  <input
                    id="request_timeout_seconds"
                    type="number"
                    min={1}
                    max={600}
                    value={form.request_timeout_seconds}
                    onChange={(e) =>
                      setForm({ ...form, request_timeout_seconds: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="max_upload_size_mb">Dung lượng tải lên tối đa (MB)</label>
                  <input
                    id="max_upload_size_mb"
                    type="number"
                    min={1}
                    max={1024}
                    value={form.max_upload_size_mb}
                    onChange={(e) =>
                      setForm({ ...form, max_upload_size_mb: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="default_language">Ngôn ngữ mặc định</label>
                  <select
                    id="default_language"
                    value={form.default_language}
                    onChange={(e) => setForm({ ...form, default_language: e.target.value })}
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                  </select>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    <Save size={15} />
                    {saving ? "Đang lưu..." : "Lưu cấu hình"}
                  </button>
                  {updatedAt && (
                    <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Cập nhật lần cuối: {new Date(updatedAt).toLocaleString("vi-VN")}
                    </span>
                  )}
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </AppLayout>
  );
}