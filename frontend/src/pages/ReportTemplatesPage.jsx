import { useEffect, useState } from "react";
import { FileBarChart, RefreshCw, Save, Eye } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  getReportFilterConfig,
  listReportTemplates,
  previewReportTemplate,
  saveReportFilterConfig,
} from "../api/reportTemplates.js";

const CATEGORY_LABELS = {
  NGAN_SACH: "Ngân sách",
  TAI_SAN_CONG: "Tài sản công",
  DAU_TU_CONG: "Đầu tư công",
  GIA: "Giá",
  TONG_HOP: "Tổng hợp",
};

const PERIOD_LABELS = {
  THANG: "Theo tháng",
  QUY: "Theo quý",
  NAM: "Theo năm",
};

const currentYear = new Date().getFullYear();

export default function ReportTemplatesPage() {
  const { user } = useAuth();
  const userId = user?.id;

  const [categoryFilter, setCategoryFilter] = useState("");
  const [templates, setTemplates] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [preview, setPreview] = useState(null);

  const [filterForm, setFilterForm] = useState({
    year: currentYear,
    periodType: "NAM",
    periodValue: "",
    orgUnitCode: "",
    sector: "",
  });
  const [savedConfig, setSavedConfig] = useState(null);

  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const selectedTemplate = templates.find((t) => t.id === selectedId) || null;

  // ---------- Bước 1: Xem danh mục mẫu báo cáo -> hệ thống hiển thị ----------
  async function loadCatalog() {
    setLoadingCatalog(true);
    setError(null);
    try {
      const data = await listReportTemplates({
        onlyActive: true,
        category: categoryFilter || null,
      });
      setTemplates(data);
      if (data.length > 0 && !data.some((t) => t.id === selectedId)) {
        setSelectedId(data[0].id);
      }
      if (data.length === 0) {
        setSelectedId(null);
      }
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingCatalog(false);
    }
  }

  useEffect(() => {
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryFilter]);

  // ---------- Bước 2: Chọn mẫu báo cáo -> hệ thống hiển thị xem trước ----------
  async function loadTemplateDetail(templateId) {
    setPreview(null);
    setSavedConfig(null);
    setInfo(null);
    setError(null);
    setLoadingPreview(true);
    try {
      const previewData = await previewReportTemplate(templateId, 5);
      setPreview(previewData);

      const template = templates.find((t) => t.id === templateId);
      setFilterForm((prev) => ({
        ...prev,
        periodType: template?.available_periods?.[0] || "NAM",
        periodValue: "",
      }));

      if (userId) {
        try {
          const existing = await getReportFilterConfig(templateId, userId);
          setSavedConfig(existing);
          setFilterForm({
            year: existing.year,
            periodType: existing.period_type,
            periodValue: existing.period_value ?? "",
            orgUnitCode: existing.org_unit_code || "",
            sector: existing.sector || "",
          });
        } catch (e) {
          // Chưa có cấu hình đã lưu — giữ nguyên form mặc định, không phải lỗi.
          if (e?.response?.status !== 404) {
            setError(e?.response?.data?.detail?.message || e.message);
          }
        }
      }
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingPreview(false);
    }
  }

  useEffect(() => {
    if (selectedId != null) {
      loadTemplateDetail(selectedId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // ---------- Bước 3: Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ) -> hệ thống lưu trạng thái ----------
  async function handleSaveFilterConfig(e) {
    e.preventDefault();
    if (!userId) {
      setError("Không xác định được người dùng hiện tại — vui lòng đăng nhập lại.");
      return;
    }
    if (!selectedTemplate) return;

    setSaving(true);
    setError(null);
    setInfo(null);
    try {
      const saved = await saveReportFilterConfig(selectedTemplate.id, {
        userId,
        year: Number(filterForm.year),
        periodType: filterForm.periodType,
        periodValue:
          filterForm.periodType === "NAM" || filterForm.periodValue === ""
            ? null
            : Number(filterForm.periodValue),
        orgUnitCode: filterForm.orgUnitCode || null,
        sector: filterForm.sector || null,
      });
      setSavedConfig(saved);
      setInfo("Đã lưu cấu hình bộ lọc cho mẫu báo cáo này.");
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSaving(false);
    }
  }

  const availablePeriods = selectedTemplate?.available_periods || ["NAM"];

  return (
    <AppLayout
      title="Chọn báo cáo theo mẫu + cấu hình bộ lọc"
      subtitle="UC-049 — Xem danh mục mẫu báo cáo, chọn 1 mẫu để xem trước, rồi cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ). Hệ thống lưu trạng thái để dùng khi sinh báo cáo (UC-050)."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}
      {info && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          {info}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 20 }}>
        {/* Cột trái — Bước 1: Danh mục mẫu báo cáo */}
        <div className="card" style={{ margin: 0 }}>
          <div className="card-header">
            <h3>Danh mục mẫu báo cáo</h3>
          </div>
          <div className="card-body">
            <div className="field" style={{ marginBottom: 12 }}>
              <label>Lĩnh vực</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">Tất cả lĩnh vực</option>
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={loadCatalog}
              disabled={loadingCatalog}
              style={{ marginBottom: 12, width: "100%" }}
            >
              <RefreshCw size={14} /> Tải lại
            </button>

            {loadingCatalog && templates.length === 0 ? (
              <p style={{ color: "#666" }}>Đang tải...</p>
            ) : templates.length === 0 ? (
              <div className="empty-state">Chưa có mẫu báo cáo nào trong danh mục.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {templates.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSelectedId(t.id)}
                    className="btn btn-secondary"
                    style={{
                      textAlign: "left",
                      justifyContent: "flex-start",
                      background: selectedId === t.id ? "var(--color-primary-soft)" : undefined,
                      borderColor: selectedId === t.id ? "var(--color-primary)" : undefined,
                    }}
                  >
                    <div>
                      <span className="badge" style={{ marginBottom: 4 }}>
                        {CATEGORY_LABELS[t.category] || t.category}
                      </span>
                      <div style={{ fontWeight: 600 }}>{t.name}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>{t.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Cột phải — Bước 2 + Bước 3 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {!selectedTemplate ? (
            <div className="card">
              <div className="card-body">
                <div className="empty-state">
                  Chọn 1 mẫu báo cáo ở danh mục bên trái để xem trước.
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Bước 2 — Xem trước */}
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Eye size={16} /> Xem trước — {selectedTemplate.name}
                  </h3>
                </div>
                <div className="card-body">
                  {loadingPreview ? (
                    <p style={{ color: "#666" }}>Đang tải bản xem trước...</p>
                  ) : preview ? (
                    <div style={{ overflowX: "auto" }}>
                      <table className="table">
                        <thead>
                          <tr>
                            {preview.columns.map((c) => (
                              <th key={c.field}>{c.label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.sample_rows.map((row, idx) => (
                            <tr key={idx}>
                              {preview.columns.map((c) => (
                                <td key={c.field}>{String(row[c.field] ?? "")}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
                        Dữ liệu minh hoạ — số liệu thật sẽ được truy vấn từ Lớp ngữ nghĩa khi
                        sinh báo cáo (UC-050).
                      </p>
                    </div>
                  ) : (
                    <div className="empty-state">Không có dữ liệu xem trước.</div>
                  )}
                </div>
              </div>

              {/* Bước 3 — Cấu hình bộ lọc */}
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <FileBarChart size={16} /> Cấu hình bộ lọc
                  </h3>
                </div>
                <div className="card-body">
                  {savedConfig && (
                    <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                      Đã có cấu hình lưu trước đó cho mẫu này — chỉnh sửa rồi lưu lại sẽ ghi
                      đè lên cấu hình cũ.
                    </p>
                  )}
                  <form onSubmit={handleSaveFilterConfig}>
                    <div className="form-grid">
                      <div className="field">
                        <label>Năm</label>
                        <input
                          type="number"
                          min={1900}
                          max={2100}
                          value={filterForm.year}
                          onChange={(e) =>
                            setFilterForm((f) => ({ ...f, year: e.target.value }))
                          }
                          required
                        />
                      </div>
                      <div className="field">
                        <label>Kỳ</label>
                        <select
                          value={filterForm.periodType}
                          onChange={(e) =>
                            setFilterForm((f) => ({
                              ...f,
                              periodType: e.target.value,
                              periodValue: "",
                            }))
                          }
                        >
                          {availablePeriods.map((p) => (
                            <option key={p} value={p}>
                              {PERIOD_LABELS[p] || p}
                            </option>
                          ))}
                        </select>
                      </div>
                      {filterForm.periodType !== "NAM" && (
                        <div className="field">
                          <label>
                            {filterForm.periodType === "THANG" ? "Tháng (1-12)" : "Quý (1-4)"}
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={filterForm.periodType === "THANG" ? 12 : 4}
                            value={filterForm.periodValue}
                            onChange={(e) =>
                              setFilterForm((f) => ({ ...f, periodValue: e.target.value }))
                            }
                            required
                          />
                        </div>
                      )}
                      <div className="field">
                        <label>Đơn vị (tuỳ chọn)</label>
                        <input
                          type="text"
                          placeholder="Mã đơn vị, để trống nếu không lọc"
                          value={filterForm.orgUnitCode}
                          onChange={(e) =>
                            setFilterForm((f) => ({ ...f, orgUnitCode: e.target.value }))
                          }
                        />
                      </div>
                      <div className="field">
                        <label>Lĩnh vực bộ lọc (tuỳ chọn)</label>
                        <select
                          value={filterForm.sector}
                          onChange={(e) =>
                            setFilterForm((f) => ({ ...f, sector: e.target.value }))
                          }
                        >
                          <option value="">Không lọc theo lĩnh vực</option>
                          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={saving}
                      style={{ marginTop: 12 }}
                    >
                      <Save size={14} /> {saving ? "Đang lưu..." : "Lưu cấu hình bộ lọc"}
                    </button>
                  </form>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}