import { useEffect, useState } from "react";
import { AlertCircle, History, PlayCircle, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import {
  getParsingJob,
  listParsedRecords,
  listParsingJobs,
  listParsingRowErrors,
  receiveParsingRequested,
} from "../../api/parsingJobs.js";

const SOURCE_FORMATS = ["", "CSV", "EXCEL", "JSON", "XML"];

const STATUS_BADGE = {
  RECEIVED: "badge-neutral",
  RUNNING: "badge-warning",
  MAPPED: "badge-success",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  RECEIVED: "Đã nhận",
  RUNNING: "Đang xử lý",
  MAPPED: "Đã ánh xạ",
  FAILED: "Thất bại",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function ParsingJobsPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [rawObjectKey, setRawObjectKey] = useState("");
  const [sourceFormat, setSourceFormat] = useState("");
  const [jobs, setJobs] = useState([]);
  const [lastJob, setLastJob] = useState(null);
  const [lastJobDetail, setLastJobDetail] = useState({ rowErrors: [], records: [] });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

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

  async function loadJobs(datasetId) {
    try {
      setJobs(await listParsingJobs({ datasetId }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    if (selectedDatasetId) {
      loadJobs(Number(selectedDatasetId));
    } else {
      setJobs([]);
    }
    setLastJob(null);
    setLastJobDetail({ rowErrors: [], records: [] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  const selectedDataset = datasets.find((d) => d.id === Number(selectedDatasetId));

  async function handleTrigger() {
    if (!selectedDataset || !rawObjectKey.trim()) return;
    setRunning(true);
    try {
      const job = await receiveParsingRequested({
        datasetId: selectedDataset.id,
        rawObjectKey: rawObjectKey.trim(),
        schemaFields: selectedDataset.schema_fields,
        sourceFormat: sourceFormat || null,
      });
      setLastJob(job);
      const [rowErrors, records] = await Promise.all([
        listParsingRowErrors(job.id),
        listParsedRecords(job.id),
      ]);
      setLastJobDetail({ rowErrors, records });
      await loadJobs(selectedDataset.id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleViewJob(id) {
    try {
      const job = await getParsingJob(id);
      const [rowErrors, records] = await Promise.all([
        listParsingRowErrors(id),
        listParsedRecords(id),
      ]);
      setLastJob(job);
      setLastJobDetail({ rowErrors, records });
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Phân tích dữ liệu có cấu trúc"
      subtitle="UC-029 — Nhận sự kiện parsing.requested, đọc dữ liệu thô vào bảng stg_*, phân tích Excel/CSV/JSON/XML theo lược đồ, ánh xạ tên trường + ép kiểu, rồi kích hoạt sự kiện mapping.requested cho UC-031."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Mô phỏng sự kiện parsing.requested (kích hoạt thủ công)</h2>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : datasets.length === 0 ? (
            <div className="empty-state">
              Chưa có tập dữ liệu nào. Định nghĩa tập dữ liệu + lược đồ (UC-018) trước.
            </div>
          ) : (
            <div className="form-grid">
              <div className="field">
                <label htmlFor="dataset">Tập dữ liệu</label>
                <select
                  id="dataset"
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                >
                  <option value="" disabled>
                    -- Chọn tập dữ liệu --
                  </option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.code} — {d.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="raw-object-key">
                  raw_object_key (đường dẫn tệp thô trên MinIO)
                </label>
                <input
                  id="raw-object-key"
                  type="text"
                  placeholder="vd: uc29/demo/du_lieu.csv"
                  value={rawObjectKey}
                  onChange={(e) => setRawObjectKey(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="source-format">Định dạng nguồn (tự suy luận nếu để trống)</label>
                <select
                  id="source-format"
                  value={sourceFormat}
                  onChange={(e) => setSourceFormat(e.target.value)}
                >
                  {SOURCE_FORMATS.map((f) => (
                    <option key={f} value={f}>
                      {f || "(tự suy luận theo đuôi tệp)"}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleTrigger}
                disabled={running || !selectedDataset || !rawObjectKey.trim()}
              >
                <PlayCircle size={15} />
                {running ? "Đang xử lý..." : "Gửi sự kiện parsing.requested"}
              </button>
            </div>
          )}
        </div>
      </div>

      {lastJob && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả phiên phân tích #{lastJob.id}</h2>
            <span className={`badge ${STATUS_BADGE[lastJob.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastJob.status] || lastJob.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Đọc được <strong>{lastJob.records_read}</strong> dòng, ánh xạ + ép kiểu thành công{" "}
              <strong>{lastJob.records_parsed}</strong>, lỗi <strong>{lastJob.records_failed}</strong>.
            </p>
            <p>
              Sự kiện mapping.requested:{" "}
              {lastJob.mapping_event_published ? (
                <span className="badge badge-success">Đã đẩy</span>
              ) : (
                <span className="badge badge-neutral">Chưa đẩy</span>
              )}
            </p>
            {lastJob.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastJob.error_message}</p>
            )}

            {lastJobDetail.rowErrors.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Lỗi từng dòng ({lastJobDetail.rowErrors.length}):</strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dòng</th>
                      <th>Trường</th>
                      <th>Thông báo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastJobDetail.rowErrors.map((e, i) => (
                      <tr key={i}>
                        <td>{e.row_index}</td>
                        <td>{e.field_name}</td>
                        <td>{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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

      {selectedDataset && (
        <div className="card">
          <div className="card-header">
            <h2>
              <History size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Lịch sử phiên phân tích của tập dữ liệu này
            </h2>
            <button
              className="icon-btn"
              title="Làm mới"
              onClick={() => loadJobs(Number(selectedDatasetId))}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {jobs.length === 0 ? (
              <div className="empty-state">Chưa có phiên phân tích nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Định dạng</th>
                    <th>Nhận lúc</th>
                    <th>Kết thúc</th>
                    <th>Trạng thái</th>
                    <th>Số bản ghi</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id}>
                      <td>{j.id}</td>
                      <td>{j.source_format}</td>
                      <td>{formatTime(j.received_at)}</td>
                      <td>{formatTime(j.completed_at)}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[j.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[j.status] || j.status}
                        </span>
                      </td>
                      <td>
                        {j.records_parsed}/{j.records_read}
                      </td>
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
      )}
    </AppLayout>
  );
}