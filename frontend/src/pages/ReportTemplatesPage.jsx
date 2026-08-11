import { useEffect, useState } from "react";
import { FileBarChart, RefreshCw, Save, Eye, PlayCircle, FileDown, FileSpreadsheet, History } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  exportReportExcel,
  exportReportPdf,
  generateReport,
  getReportFilterConfig,
  listGeneratedReportLogs,
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

  // ---------- UC-050: Sinh + kết xuất báo cáo ----------
  const [generatedReport, setGeneratedReport] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [reportError, setReportError] = useState(null);
  const [reportInfo, setReportInfo] = useState(null);
  const [reportLogs, setReportLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

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
    setGeneratedReport(null);
    setReportError(null);
    setReportInfo(null);
    setReportLogs([]);
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

  // ---------- UC-050 bước 1: Sinh báo cáo theo mẫu + bộ lọc ----------
  // -> Hệ thống truy vấn Lớp ngữ nghĩa + kết xuất.
  function _currentFilters() {
    return {
      userId,
      year: filterForm.year ? Number(filterForm.year) : null,
      periodType: filterForm.periodType || null,
      periodValue:
        filterForm.periodType === "NAM" || filterForm.periodValue === ""
          ? null
          : Number(filterForm.periodValue),
      orgUnitCode: filterForm.orgUnitCode || null,
      sector: filterForm.sector || null,
    };
  }

  async function loadReportLogs(templateId) {
    if (!userId) return;
    setLoadingLogs(true);
    try {
      const logs = await listGeneratedReportLogs(templateId, userId);
      setReportLogs(logs);
    } catch (e) {
      // Lịch sử không tải được không phải lỗi chặn — chỉ hiển thị rỗng.
      setReportLogs([]);
    } finally {
      setLoadingLogs(false);
    }
  }

  async function handleGenerateReport() {
    if (!userId || !selectedTemplate) {
      setReportError("Không xác định được người dùng hiện tại — vui lòng đăng nhập lại.");
      return;
    }
    setGenerating(true);
    setReportError(null);
    setReportInfo(null);
    try {
      const report = await generateReport(selectedTemplate.id, _currentFilters());
      setGeneratedReport(report);
      setReportInfo(`Đã sinh báo cáo với ${report.row_count} dòng dữ liệu.`);
    } catch (e) {
      setReportError(e?.response?.data?.detail?.message || e.message);
      setGeneratedReport(null);
    } finally {
      setGenerating(false);
    }
  }

  // ---------- UC-050 bước 2: Kết xuất PDF -> Hệ thống trả file ----------
  async function handleExportPdf() {
    if (!userId || !selectedTemplate) return;
    setExportingPdf(true);
    setReportError(null);
    setReportInfo(null);
    try {
      const filename = await exportReportPdf(selectedTemplate.id, _currentFilters());
      setReportInfo(`Đã tải xuống file PDF: ${filename}`);
      await loadReportLogs(selectedTemplate.id);
    } catch (e) {
      setReportError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setExportingPdf(false);
    }
  }

  // ---------- UC-050 bước 3: Kết xuất Excel -> Hệ thống trả file ----------
  async function handleExportExcel() {
    if (!userId || !selectedTemplate) return;
    setExportingExcel(true);
    setReportError(null);
    setReportInfo(null);
    try {
      const filename = await exportReportExcel(selectedTemplate.id, _currentFilters());
      setReportInfo(`Đã tải xuống file Excel: ${filename}`);
      await loadReportLogs(selectedTemplate.id);
    } catch (e) {
      setReportError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setExportingExcel(false);
    }
  }

  useEffect(() => {
    if (selectedId != null && userId) {
      loadReportLogs(selectedId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, userId]);

  return (
    <AppLayout
      title="Chọn báo cáo theo mẫu + cấu hình bộ lọc"
      subtitle="UC-049 — Xem danh mục mẫu báo cáo, chọn 1 mẫu để xem trước, rồi cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ). UC-050 — Sinh + kết xuất báo cáo theo đúng bộ lọc đó (PDF/Excel)."
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

              {/* UC-050 — Sinh + kết xuất báo cáo */}
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <PlayCircle size={16} /> Sinh + kết xuất báo cáo
                  </h3>
                </div>
                <div className="card-body">
                  <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                    Dùng đúng bộ lọc ở khung trên (chưa lưu cũng được sinh thử). Nếu để trống toàn
                    bộ khung bộ lọc, hệ thống dùng lại cấu hình đã lưu (UC-049).
                  </p>

                  {reportError && (
                    <div className="alert alert-error" style={{ marginBottom: 10 }}>
                      {reportError}
                    </div>
                  )}
                  {reportInfo && (
                    <div className="alert alert-success" style={{ marginBottom: 10 }}>
                      {reportInfo}
                    </div>
                  )}

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleGenerateReport}
                      disabled={generating}
                    >
                      <PlayCircle size={14} /> {generating ? "Đang sinh..." : "Sinh báo cáo (xem trước)"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleExportPdf}
                      disabled={exportingPdf}
                    >
                      <FileDown size={14} /> {exportingPdf ? "Đang xuất..." : "Kết xuất PDF"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleExportExcel}
                      disabled={exportingExcel}
                    >
                      <FileSpreadsheet size={14} />{" "}
                      {exportingExcel ? "Đang xuất..." : "Kết xuất Excel"}
                    </button>
                  </div>

                  {generatedReport && (
                    <div style={{ overflowX: "auto", marginBottom: 16 }}>
                      <p style={{ fontSize: 12, color: "#666", marginBottom: 6 }}>
                        Bộ lọc đã dùng: Năm {generatedReport.filters.year} —{" "}
                        {PERIOD_LABELS[generatedReport.filters.period_type] ||
                          generatedReport.filters.period_type}
                        {generatedReport.filters.period_value
                          ? ` ${generatedReport.filters.period_value}`
                          : ""}
                        {generatedReport.filters.org_unit_code
                          ? ` — Đơn vị: ${generatedReport.filters.org_unit_code}`
                          : ""}
                        {generatedReport.filters.sector
                          ? ` — Lĩnh vực: ${CATEGORY_LABELS[generatedReport.filters.sector] || generatedReport.filters.sector}`
                          : ""}
                        {" — "}Tổng số dòng: {generatedReport.row_count}
                      </p>
                      <table className="table">
                        <thead>
                          <tr>
                            {generatedReport.columns.map((c) => (
                              <th key={c.field}>{c.label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {generatedReport.rows.map((row, idx) => (
                            <tr key={idx}>
                              {generatedReport.columns.map((c) => (
                                <td key={c.field}>{String(row[c.field] ?? "")}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <h4 style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                    <History size={14} /> Lịch sử kết xuất
                  </h4>
                  {loadingLogs ? (
                    <p style={{ color: "#666" }}>Đang tải lịch sử...</p>
                  ) : reportLogs.length === 0 ? (
                    <div className="empty-state">Chưa có lượt kết xuất nào cho mẫu này.</div>
                  ) : (
                    <div style={{ overflowX: "auto" }}>
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Định dạng</th>
                            <th>Năm</th>
                            <th>Kỳ</th>
                            <th>Đơn vị</th>
                            <th>Lĩnh vực</th>
                            <th>Số dòng</th>
                            <th>Thời điểm</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportLogs.map((log) => (
                            <tr key={log.id}>
                              <td>
                                <span className="badge">{log.format}</span>
                              </td>
                              <td>{log.year}</td>
                              <td>
                                {PERIOD_LABELS[log.period_type] || log.period_type}
                                {log.period_value ? ` ${log.period_value}` : ""}
                              </td>
                              <td>{log.org_unit_code || "-"}</td>
                              <td>{CATEGORY_LABELS[log.sector] || log.sector || "-"}</td>
                              <td>{log.row_count}</td>
                              <td>
                                {log.generated_at
                                  ? new Date(log.generated_at).toLocaleString("vi-VN")
                                  : "-"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}