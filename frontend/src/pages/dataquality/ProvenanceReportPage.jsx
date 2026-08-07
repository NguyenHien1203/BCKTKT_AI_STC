import { useState } from "react";
import { AlertCircle, CheckCircle2, FileOutput } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  PROVENANCE_SCOPE_LABELS,
  exportProvenanceReportPdf,
  previewProvenanceReport,
} from "../../api/provenanceReports.js";
import { LINEAGE_STEPS, LINEAGE_STEP_LABELS } from "../../api/recordLineage.js";

const SCOPE_PLACEHOLDER = {
  DATASET: "Nhập dataset_id, vd: 4501",
  RECORD: "Nhập curated_dm_record_id, vd: 12",
  SOURCE: "Nhập data_source_id, vd: 3",
};

const SCOPE_HELP = {
  DATASET: "Toàn bộ bản ghi đã công bố (dm_*) của 1 tập dữ liệu.",
  RECORD: "Đúng 1 bản ghi curated — báo cáo kèm chi tiết đầy đủ từng bước (thô/phân tích/ánh xạ/chất lượng/công bố).",
  SOURCE: "Toàn bộ bản ghi thuộc các tập dữ liệu có dữ liệu thô lấy từ 1 nguồn dữ liệu (data_source_id).",
};

function StepBadges({ steps }) {
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {steps.map((s) => (
        <span
          key={s.step}
          title={s.note || s.status || ""}
          className={s.available ? "badge badge-success" : "badge badge-danger"}
          style={{ fontSize: 11 }}
        >
          {LINEAGE_STEP_LABELS[s.step] || s.step}
          {s.status ? ` · ${s.status}` : ""}
        </span>
      ))}
    </div>
  );
}

function JsonBlock({ value }) {
  if (value === null || value === undefined) {
    return <span style={{ color: "var(--muted)" }}>— (không có dữ liệu)</span>;
  }
  return (
    <pre
      style={{
        background: "var(--surface-alt, #f4f4f5)",
        borderRadius: 8,
        padding: 10,
        fontSize: 12,
        overflowX: "auto",
        margin: 0,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function ProvenanceReportPage() {
  const [scopeType, setScopeType] = useState("DATASET");
  const [scopeValue, setScopeValue] = useState("");
  const [includeStepDetails, setIncludeStepDetails] = useState(false);
  const [limit, setLimit] = useState(50);

  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportedFilename, setExportedFilename] = useState(null);

  // Bước 1 "Chọn phạm vi" + bước 2 "Sinh báo cáo nguồn gốc dữ liệu" (xem trước).
  async function handlePreview(e) {
    e?.preventDefault();
    if (!scopeValue.trim()) {
      setError("Vui lòng nhập mã của phạm vi đã chọn.");
      return;
    }
    setLoading(true);
    setError(null);
    setExportedFilename(null);
    try {
      const data = await previewProvenanceReport({
        scopeType,
        scopeValue: scopeValue.trim(),
        limit,
        includeStepDetails: scopeType === "RECORD" ? true : includeStepDetails,
      });
      setReport(data);
    } catch (err) {
      setReport(null);
      setError(err?.response?.data?.detail?.message || err.message);
    } finally {
      setLoading(false);
    }
  }

  // Bước 2 "Sinh báo cáo" -> "Hệ thống kết xuất PDF" -> bước 3 "Kết xuất
  // PDF" -> "Hệ thống trả file".
  async function handleExportPdf() {
    if (!scopeValue.trim()) {
      setError("Vui lòng nhập mã của phạm vi đã chọn.");
      return;
    }
    setExporting(true);
    setError(null);
    setExportedFilename(null);
    try {
      const filename = await exportProvenanceReportPdf({
        scopeType,
        scopeValue: scopeValue.trim(),
        limit,
        includeStepDetails: scopeType === "RECORD" ? true : includeStepDetails,
      });
      setExportedFilename(filename);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || err.message);
    } finally {
      setExporting(false);
    }
  }

  return (
    <AppLayout
      title="Xuất báo cáo nguồn gốc dữ liệu"
      subtitle="UC-046 — Kiểm toán viên chọn phạm vi (tập dữ liệu / bản ghi / nguồn), hệ thống hiển thị + sinh báo cáo, kết xuất PDF và trả file."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {exportedFilename && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          <CheckCircle2 size={16} />
          <span>
            Đã tải xuống: <code>{exportedFilename}</code>
          </span>
        </div>
      )}

      {/* ---------- Bước 1: Chọn phạm vi ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bước 1 — Chọn phạm vi</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handlePreview} className="form-grid">
            <div className="field">
              <label htmlFor="scope-type">Phạm vi</label>
              <select
                id="scope-type"
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value)}
              >
                {Object.entries(PROVENANCE_SCOPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="scope-value">Mã ({PROVENANCE_SCOPE_LABELS[scopeType]})</label>
              <input
                id="scope-value"
                type="text"
                value={scopeValue}
                onChange={(e) => setScopeValue(e.target.value)}
                placeholder={SCOPE_PLACEHOLDER[scopeType]}
              />
            </div>
            <div className="field">
              <label htmlFor="scope-limit">Giới hạn số bản ghi</label>
              <input
                id="scope-limit"
                type="number"
                min={1}
                max={500}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value) || 50)}
              />
            </div>
            {scopeType !== "RECORD" && (
              <div className="field" style={{ justifyContent: "flex-end" }}>
                <label htmlFor="include-step-details" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    id="include-step-details"
                    type="checkbox"
                    checked={includeStepDetails}
                    onChange={(e) => setIncludeStepDetails(e.target.checked)}
                  />
                  Kèm chi tiết từng bước (nặng hơn)
                </label>
              </div>
            )}
            <div className="field field-full" style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Đang tải..." : "Xem trước báo cáo"}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={exporting}
                onClick={handleExportPdf}
              >
                <FileOutput size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                {exporting ? "Đang kết xuất..." : "Kết xuất PDF"}
              </button>
            </div>
          </form>
          <p style={{ fontSize: 12.5, color: "var(--color-text-secondary)", marginTop: 8 }}>
            {SCOPE_HELP[scopeType]}
          </p>
        </div>
      </div>

      {report && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>
              Bước 2 — Báo cáo: {report.scope_label} (mã = {report.scope_value})
            </h2>
          </div>
          <div className="card-body">
            <p style={{ fontSize: 13 }}>
              Thời điểm sinh: {report.generated_at} · Tổng số bản ghi khớp phạm vi:{" "}
              <b>{report.total_matched}</b> · Số bản ghi trong báo cáo: <b>{report.returned_count}</b>
              {report.truncated ? " (đã cắt bớt theo giới hạn)" : ""} · Truy vết đầy đủ 5 bước:{" "}
              <b>
                {report.fully_traced_count}/{report.returned_count}
              </b>
            </p>

            <table className="table" style={{ width: "100%", fontSize: 13 }}>
              <thead>
                <tr>
                  <th>Bản ghi (id)</th>
                  <th>Tập dữ liệu</th>
                  <th>Dòng #</th>
                  <th>Chuỗi nguồn gốc</th>
                </tr>
              </thead>
              <tbody>
                {report.records.map((r) => (
                  <tr key={r.curated_dm_record_id}>
                    <td>{r.curated_dm_record_id}</td>
                    <td>{r.dataset_id ?? "—"}</td>
                    <td>{r.row_index}</td>
                    <td>
                      <StepBadges steps={r.chain.steps} />
                    </td>
                  </tr>
                ))}
                {report.records.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty-state">
                      Không có bản ghi nào khớp phạm vi đã chọn.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {report && report.records.some((r) => r.step_details) && (
        <div className="card">
          <div className="card-header">
            <h2>Bước 3 — Chi tiết từng bước (dữ liệu vào/ra + phép biến đổi)</h2>
          </div>
          <div className="card-body">
            {report.records
              .filter((r) => r.step_details)
              .map((r) => (
                <div
                  key={r.curated_dm_record_id}
                  style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 12, marginBottom: 12 }}
                >
                  <b>
                    Bản ghi curated #{r.curated_dm_record_id} — tập dữ liệu {r.dataset_id ?? "—"} — dòng #
                    {r.row_index}
                  </b>
                  {LINEAGE_STEPS.map((step) => {
                    const detail = r.step_details.find((d) => d.step === step);
                    if (!detail) return null;
                    return (
                      <div key={step} style={{ marginTop: 10 }}>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>
                          {detail.label} ({detail.step}){" "}
                          {!detail.available && (
                            <span className="badge badge-danger" style={{ fontSize: 11 }}>
                              Không có dữ liệu
                            </span>
                          )}
                        </div>
                        {detail.note && (
                          <p style={{ fontSize: 12.5, color: "var(--color-text-secondary)" }}>Ghi chú: {detail.note}</p>
                        )}
                        {detail.transformation && (
                          <p style={{ fontSize: 12.5 }}>Phép biến đổi: {detail.transformation}</p>
                        )}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                          <div>
                            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Đầu vào</div>
                            <JsonBlock value={detail.input} />
                          </div>
                          <div>
                            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Đầu ra</div>
                            <JsonBlock value={detail.output} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
          </div>
        </div>
      )}
    </AppLayout>
  );
}