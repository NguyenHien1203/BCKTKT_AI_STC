import { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import { listDmRecords } from "../../api/curatedPublish.js";
import {
  LINEAGE_STEPS,
  LINEAGE_STEP_LABELS,
  getLineageChain,
  getLineageStepDetail,
} from "../../api/recordLineage.js";

const STEP_STATUS_BADGE = {
  MAPPED: "badge-success",
  PASSED: "badge-success",
  COMPLETED: "badge-success",
  approved: "badge-success",
  OK: "badge-success",
  RUNNING: "badge-warning",
  RECEIVED: "badge-warning",
  "BỊ TỪ CHỐI": "badge-danger",
  LỖI: "badge-danger",
  FAILED: "badge-danger",
  BELOW_THRESHOLD: "badge-danger",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
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
        padding: 12,
        fontSize: 12.5,
        overflowX: "auto",
        margin: 0,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function RecordLineagePage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [curatedRecords, setCuratedRecords] = useState([]);

  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [chain, setChain] = useState(null);
  const [selectedStep, setSelectedStep] = useState("RAW");
  const [stepDetail, setStepDetail] = useState(null);

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingChain, setLoadingChain] = useState(false);
  const [loadingStep, setLoadingStep] = useState(false);

  async function loadDatasets() {
    setLoading(true);
    try {
      setDatasets(await listDatasets({}));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCuratedRecords(datasetId) {
    if (!datasetId) {
      setCuratedRecords([]);
      return;
    }
    setLoading(true);
    try {
      const records = await listDmRecords({ datasetId: Number(datasetId) });
      setCuratedRecords(records);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    setSelectedRecordId("");
    setChain(null);
    setStepDetail(null);
    loadCuratedRecords(selectedDatasetId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  // Bước 1 "Chọn bản ghi curated": chọn 1 dòng -> bước 2 hệ thống hiển thị chuỗi
  async function handleSelectRecord(recordId) {
    setSelectedRecordId(recordId);
    setChain(null);
    setStepDetail(null);
    setSelectedStep("RAW");
    if (!recordId) return;
    setLoadingChain(true);
    try {
      const c = await getLineageChain(recordId);
      setChain(c);
      setError(null);
      await handleSelectStep(recordId, "RAW");
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingChain(false);
    }
  }

  // Bước 3 "Xem chi tiết từng bước"
  async function handleSelectStep(recordId, step) {
    const rid = recordId ?? selectedRecordId;
    if (!rid) return;
    setSelectedStep(step);
    setLoadingStep(true);
    try {
      const detail = await getLineageStepDetail(rid, step);
      setStepDetail(detail);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingStep(false);
    }
  }

  return (
    <AppLayout
      title="Truy vết nguồn gốc bản ghi"
      subtitle="UC-045 — Kiểm toán viên chọn 1 bản ghi trong kho chuẩn hoá (curated) rồi xem lại toàn bộ nguồn gốc: thô → phân tích → ánh xạ → chất lượng → công bố."
    >
      {error && (
        <div className="alert alert-danger" style={{ marginBottom: 16 }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 16, alignItems: "start" }}>
        {/* Cột trái: Bước 1 — Chọn bản ghi curated */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 1 — Chọn bản ghi curated</h2>
            <button
              className="icon-btn"
              title="Làm mới"
              onClick={() => loadCuratedRecords(selectedDatasetId)}
              disabled={loading || !selectedDatasetId}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="lineage-dataset">Tập dữ liệu</label>
                <select
                  id="lineage-dataset"
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                >
                  <option value="">-- Chọn tập dữ liệu --</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} (#{d.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ maxHeight: 480, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
              {curatedRecords.length === 0 && (
                <div style={{ color: "var(--muted)", fontSize: 13 }}>
                  {selectedDatasetId
                    ? "Chưa có bản ghi curated nào cho tập dữ liệu này."
                    : "Chọn tập dữ liệu để xem danh sách bản ghi curated."}
                </div>
              )}
              {curatedRecords.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleSelectRecord(r.id)}
                  className={selectedRecordId === r.id ? "list-item list-item-active" : "list-item"}
                  style={{
                    textAlign: "left",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "8px 10px",
                    background: selectedRecordId === r.id ? "var(--primary-bg, #eef2ff)" : "transparent",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    Bản ghi #{r.id} — dòng {r.row_index}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>
                    publish_status={r.publish_status} · version={r.version} · {formatTime(r.last_published_at)}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Cột phải: Bước 2 + Bước 3 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <h2>Bước 2 — Chuỗi nguồn gốc (thô → phân tích → ánh xạ → chất lượng → công bố)</h2>
            </div>
            <div className="card-body">
              {!selectedRecordId && (
                <div style={{ color: "var(--muted)" }}>Chọn 1 bản ghi curated ở cột trái để xem chuỗi nguồn gốc.</div>
              )}
              {loadingChain && <div>Đang tải chuỗi nguồn gốc…</div>}
              {chain && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {chain.steps.map((s, idx) => (
                    <div key={s.step} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <button
                        onClick={() => handleSelectStep(selectedRecordId, s.step)}
                        disabled={!s.available}
                        style={{
                          border: selectedStep === s.step ? "2px solid var(--primary, #4f46e5)" : "1px solid var(--border)",
                          borderRadius: 10,
                          padding: "10px 14px",
                          minWidth: 150,
                          textAlign: "left",
                          background: s.available ? "var(--surface, #fff)" : "var(--surface-alt, #f4f4f5)",
                          cursor: s.available ? "pointer" : "not-allowed",
                          opacity: s.available ? 1 : 0.6,
                        }}
                      >
                        <div style={{ fontSize: 12, color: "var(--muted)" }}>Bước {idx + 1}</div>
                        <div style={{ fontWeight: 700 }}>{s.label}</div>
                        {s.status && (
                          <span className={`badge ${STEP_STATUS_BADGE[s.status] || "badge-default"}`} style={{ marginTop: 4, display: "inline-block" }}>
                            {s.status}
                          </span>
                        )}
                        {s.job_id != null && (
                          <div style={{ fontSize: 11, color: "var(--muted)" }}>job #{s.job_id}</div>
                        )}
                        {s.note && (
                          <div style={{ fontSize: 11, color: "var(--danger, #dc2626)" }}>{s.note}</div>
                        )}
                      </button>
                      {idx < chain.steps.length - 1 && <span style={{ color: "var(--muted)" }}>→</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Bước 3 — Chi tiết bước: {LINEAGE_STEP_LABELS[selectedStep] || selectedStep}</h2>
            </div>
            <div className="card-body">
              {!chain && <div style={{ color: "var(--muted)" }}>Chưa có dữ liệu.</div>}
              {chain && (
                <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
                  {LINEAGE_STEPS.map((step) => (
                    <button
                      key={step}
                      className={selectedStep === step ? "btn btn-primary" : "btn btn-secondary"}
                      onClick={() => handleSelectStep(selectedRecordId, step)}
                    >
                      {LINEAGE_STEP_LABELS[step]}
                    </button>
                  ))}
                </div>
              )}
              {loadingStep && <div>Đang tải chi tiết bước…</div>}
              {stepDetail && !loadingStep && (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {!stepDetail.available && (
                    <div className="alert alert-warning">
                      Không có dữ liệu cho bước này{stepDetail.note ? `: ${stepDetail.note}` : "."}
                    </div>
                  )}
                  {stepDetail.transformation && (
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Phép biến đổi</div>
                      <div style={{ fontSize: 13.5 }}>{stepDetail.transformation}</div>
                    </div>
                  )}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Dữ liệu vào</div>
                      <JsonBlock value={stepDetail.input} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Dữ liệu ra</div>
                      <JsonBlock value={stepDetail.output} />
                    </div>
                  </div>
                  {stepDetail.meta && Object.keys(stepDetail.meta).length > 0 && (
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Thông tin thêm (job, quy tắc, lỗi…)</div>
                      <JsonBlock value={stepDetail.meta} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}