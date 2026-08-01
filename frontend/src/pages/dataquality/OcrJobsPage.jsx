import { useEffect, useState } from "react";
import { AlertCircle, History, PlayCircle, RefreshCw, Table2 } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listVanBanDocuments } from "../../api/vanBanIntake.js";
import {
  getOcrJob,
  listOcrJobs,
  listOcrTables,
  receiveOcrRequested,
} from "../../api/ocrJobs.js";

const ENGINES = ["", "PADDLEOCR", "OLMOCR"];

const STATUS_BADGE = {
  RECEIVED: "badge-neutral",
  RUNNING: "badge-warning",
  COMPLETED: "badge-success",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  RECEIVED: "Đã nhận",
  RUNNING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function OcrJobsPage() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [rawObjectKey, setRawObjectKey] = useState("");
  const [engine, setEngine] = useState("");
  const [jobs, setJobs] = useState([]);
  const [lastJob, setLastJob] = useState(null);
  const [lastJobTables, setLastJobTables] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  async function loadDocuments() {
    setLoading(true);
    try {
      setDocuments(await listVanBanDocuments({}));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobs() {
    try {
      setJobs(await listOcrJobs({}));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadDocuments();
    loadJobs();
  }, []);

  const selectedDoc = documents.find((d) => d.id === Number(selectedDocId));

  useEffect(() => {
    if (selectedDoc) {
      setRawObjectKey(selectedDoc.raw_object_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDocId]);

  async function handleTrigger() {
    if (!rawObjectKey.trim()) return;
    setRunning(true);
    try {
      const job = await receiveOcrRequested({
        rawObjectKey: rawObjectKey.trim(),
        vanBanIntakeId: selectedDoc ? selectedDoc.id : null,
        dataSourceId: selectedDoc ? selectedDoc.data_source_id : null,
        soKyHieu: selectedDoc ? selectedDoc.so_ky_hieu : null,
        engine: engine || null,
      });
      setLastJob(job);
      setLastJobTables(await listOcrTables(job.id));
      await loadJobs();
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleViewJob(id) {
    try {
      const job = await getOcrJob(id);
      setLastJob(job);
      setLastJobTables(await listOcrTables(id));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Phân tích PDF/bản quét + OCR"
      subtitle="UC-030 — Nhận sự kiện ocr.requested, đọc file PDF/scan (bucket raw-documents), chạy OCR PaddleOCR/olmOCR, trích xuất văn bản + bảng, lưu dữ liệu có cấu trúc rồi kích hoạt sự kiện ocr.completed + parsing.requested cho UC-029."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Mô phỏng sự kiện ocr.requested (kích hoạt thủ công)</h2>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : (
            <div className="form-grid">
              <div className="field">
                <label htmlFor="van-ban-doc">
                  Văn bản đã tiếp nhận (UC-024, tuỳ chọn — tự điền raw_object_key)
                </label>
                <select
                  id="van-ban-doc"
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                >
                  <option value="">-- Không chọn (nhập tay bên dưới) --</option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      #{d.id} — {d.so_ky_hieu} ({d.loai_van_ban})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="raw-object-key">
                  raw_object_key (đường dẫn tệp PDF/scan trên MinIO, bucket raw-documents)
                </label>
                <input
                  id="raw-object-key"
                  type="text"
                  placeholder="vd: raw-documents/uc30/demo/vanban.pdf"
                  value={rawObjectKey}
                  onChange={(e) => setRawObjectKey(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="engine">Công cụ OCR (mặc định PADDLEOCR nếu để trống)</label>
                <select id="engine" value={engine} onChange={(e) => setEngine(e.target.value)}>
                  {ENGINES.map((f) => (
                    <option key={f} value={f}>
                      {f || "(mặc định PADDLEOCR)"}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleTrigger}
                disabled={running || !rawObjectKey.trim()}
              >
                <PlayCircle size={15} />
                {running ? "Đang xử lý..." : "Gửi sự kiện ocr.requested"}
              </button>
            </div>
          )}
        </div>
      </div>

      {lastJob && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả phiên OCR #{lastJob.id}</h2>
            <span className={`badge ${STATUS_BADGE[lastJob.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastJob.status] || lastJob.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Công cụ yêu cầu: <strong>{lastJob.engine_requested}</strong>
              {lastJob.engine_used && (
                <>
                  {" "}
                  — đã dùng: <strong>{lastJob.engine_used}</strong>
                </>
              )}
              . Số trang đã xử lý: <strong>{lastJob.pages_processed}</strong>. Số bảng trích
              xuất được: <strong>{lastJob.table_count}</strong>.
            </p>
            <p>
              Sự kiện ocr.completed:{" "}
              {lastJob.ocr_completed_published ? (
                <span className="badge badge-success">Đã đẩy</span>
              ) : (
                <span className="badge badge-neutral">Chưa đẩy</span>
              )}
              {"  "}
              Sự kiện parsing.requested:{" "}
              {lastJob.parsing_requested_published ? (
                <span className="badge badge-success">Đã đẩy</span>
              ) : (
                <span className="badge badge-neutral">Chưa đẩy</span>
              )}
            </p>
            {lastJob.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastJob.error_message}</p>
            )}

            {lastJob.extracted_text && (
              <div style={{ marginTop: 10 }}>
                <strong>Văn bản trích xuất:</strong>
                <pre
                  style={{
                    background: "var(--color-bg-secondary, #f5f5f5)",
                    padding: 10,
                    borderRadius: 6,
                    fontSize: 12,
                    whiteSpace: "pre-wrap",
                    maxHeight: 240,
                    overflow: "auto",
                  }}
                >
                  {lastJob.extracted_text}
                </pre>
              </div>
            )}

            {lastJobTables.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>
                  <Table2 size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                  Bảng trích xuất ({lastJobTables.length}):
                </strong>
                {lastJobTables.map((t) => (
                  <div key={t.id} style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary, #666)" }}>
                      Bảng #{t.table_index} — trang {t.page_number}
                    </div>
                    <table className="data-table">
                      <tbody>
                        {t.rows.map((row, ri) => (
                          <tr key={ri}>
                            {row.map((cell, ci) => (
                              <td key={ci}>{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 10 }}>
              <strong>Nhật ký:</strong>
              <pre
                style={{
                  background: "var(--color-bg-secondary, #f5f5f5)",
                  padding: 10,
                  borderRadius: 6,
                  fontSize: 12,
                  whiteSpace: "pre-wrap",
                }}
              >
                {lastJob.log_entries
                  .map((e) => `[${formatTime(e.timestamp)}] ${e.level} — ${e.message}`)
                  .join("\n")}
              </pre>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>
            <History size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Lịch sử phiên OCR
          </h2>
          <button className="icon-btn" title="Làm mới" onClick={loadJobs}>
            <RefreshCw size={15} />
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {jobs.length === 0 ? (
            <div className="empty-state">Chưa có phiên OCR nào.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Số ký hiệu</th>
                  <th>Công cụ</th>
                  <th>Nhận lúc</th>
                  <th>Kết thúc</th>
                  <th>Trạng thái</th>
                  <th>Số bảng</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td>{j.id}</td>
                    <td>{j.so_ky_hieu || "—"}</td>
                    <td>{j.engine_used || j.engine_requested}</td>
                    <td>{formatTime(j.received_at)}</td>
                    <td>{formatTime(j.completed_at)}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[j.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[j.status] || j.status}
                      </span>
                    </td>
                    <td>{j.table_count}</td>
                    <td>
                      <button className="icon-btn" title="Xem chi tiết" onClick={() => handleViewJob(j.id)}>
                        Xem
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  );
}