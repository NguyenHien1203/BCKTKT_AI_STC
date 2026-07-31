import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Clock, History, PlayCircle, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import { listDatasets } from "../../api/datasets.js";
import { listRunHistory } from "../../api/ingestionRuns.js";
import { getIncrementalSyncCheckpoint, runIncrementalSync } from "../../api/incrementalSync.js";

// UC-025 chỉ áp dụng cho các nguồn cho phép kết nối API/DB: MISA (nếu nhà
// cung cấp cho phép), QL Giá, PMSTT — đúng theo docs/use_cases.json id=25.
const SUPPORTED_SOURCE_SYSTEMS = ["MISA", "QL_GIA", "PMSTT"];

const STATUS_BADGE = {
  RUNNING: "badge-warning",
  SUCCESS: "badge-success",
  FAILED: "badge-danger",
  PARTIAL: "badge-warning",
};

const STATUS_LABEL = {
  RUNNING: "Đang chạy",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
  PARTIAL: "Một phần",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function IncrementalSyncPage() {
  const [dataSources, setDataSources] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [checkpoint, setCheckpoint] = useState(null);
  const [history, setHistory] = useState([]);
  const [lastRun, setLastRun] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  async function loadCatalog() {
    setLoading(true);
    try {
      const [sourcesData, datasetsData] = await Promise.all([
        listDataSources({}),
        listDatasets({}),
      ]);
      setDataSources(sourcesData);
      setDatasets(datasetsData);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCatalog();
  }, []);

  // Chỉ hiển thị các dataset thuộc nguồn MISA/QL Giá/PMSTT — đúng phạm vi UC-025.
  const eligibleDatasets = useMemo(() => {
    const sourceById = new Map(dataSources.map((s) => [s.id, s]));
    return datasets
      .filter((d) => {
        const source = sourceById.get(d.data_source_id);
        return source && SUPPORTED_SOURCE_SYSTEMS.includes(source.source_system);
      })
      .map((d) => ({ ...d, _source: sourceById.get(d.data_source_id) }));
  }, [dataSources, datasets]);

  async function loadDatasetState(datasetId) {
    try {
      const [ckpt, runs] = await Promise.all([
        getIncrementalSyncCheckpoint(datasetId),
        listRunHistory({ datasetId }),
      ]);
      setCheckpoint(ckpt.checkpoint);
      setHistory(runs.filter((r) => r.sync_mode === "INCREMENTAL").slice(0, 10));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    if (selectedDatasetId) {
      loadDatasetState(Number(selectedDatasetId));
      setLastRun(null);
    } else {
      setCheckpoint(null);
      setHistory([]);
      setLastRun(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  async function handleRun() {
    if (!selectedDatasetId) return;
    setRunning(true);
    try {
      const run = await runIncrementalSync(Number(selectedDatasetId), { trigger: "MANUAL" });
      setLastRun(run);
      await loadDatasetState(Number(selectedDatasetId));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  const selectedDataset = eligibleDatasets.find((d) => d.id === Number(selectedDatasetId));

  return (
    <AppLayout
      title="Đồng bộ tăng dần từ API/DB"
      subtitle="UC-025 — Tác vụ điều phối đọc điểm kiểm tra từ ingestion.runs, truy vấn tăng dần theo updated_at, lưu raw vào MinIO + cập nhật điểm kiểm tra, kích hoạt sự kiện parsing.requested. Áp dụng cho MISA (nếu nhà cung cấp cho phép kết nối API), QL Giá, PMSTT."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Chọn tập dữ liệu</h2>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : eligibleDatasets.length === 0 ? (
            <div className="empty-state">
              Chưa có tập dữ liệu nào thuộc nguồn MISA/QL Giá/PMSTT. Đăng ký nguồn dữ liệu (UC-015)
              và định nghĩa tập dữ liệu (UC-018) trước.
            </div>
          ) : (
            <div className="form-grid">
              <div className="field">
                <label htmlFor="dataset">Tập dữ liệu (chỉ MISA / QL Giá / PMSTT)</label>
                <select
                  id="dataset"
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                >
                  <option value="" disabled>
                    -- Chọn tập dữ liệu --
                  </option>
                  {eligibleDatasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      [{d._source.source_system}] {d.code} — {d.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedDataset && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Điểm kiểm tra (checkpoint) hiện tại</h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <Clock size={16} />
              <span>
                {checkpoint
                  ? `Đã đồng bộ tới updated_at = ${formatTime(checkpoint)}`
                  : "Chưa từng đồng bộ tăng dần lần nào — lần chạy tới sẽ đồng bộ từ đầu."}
              </span>
            </div>
            <button className="btn btn-primary" onClick={handleRun} disabled={running}>
              <PlayCircle size={15} />
              {running ? "Đang chạy..." : "Chạy đồng bộ tăng dần ngay (thủ công)"}
            </button>
          </div>
        </div>
      )}

      {lastRun && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả lần chạy vừa rồi</h2>
            <span className={`badge ${STATUS_BADGE[lastRun.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastRun.status] || lastRun.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Đọc được <strong>{lastRun.records_read}</strong> bản ghi mới/thay đổi, nạp thành công{" "}
              <strong>{lastRun.records_loaded}</strong>, lỗi <strong>{lastRun.records_failed}</strong>.
            </p>
            {lastRun.control_totals?.raw_object_key && (
              <p>
                Đã lưu dữ liệu thô vào MinIO tại: <code>{lastRun.control_totals.raw_object_key}</code>
              </p>
            )}
            {lastRun.control_totals?.last_synced_updated_at && (
              <p>
                Điểm kiểm tra mới: <code>{lastRun.control_totals.last_synced_updated_at}</code>
              </p>
            )}
            {lastRun.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastRun.error_message}</p>
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
                {lastRun.log_entries
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
              Lịch sử đồng bộ tăng dần gần đây
            </h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadDatasetState(Number(selectedDatasetId))}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {history.length === 0 ? (
              <div className="empty-state">Chưa có phiên đồng bộ tăng dần nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Kích hoạt</th>
                    <th>Bắt đầu</th>
                    <th>Kết thúc</th>
                    <th>Trạng thái</th>
                    <th>Số bản ghi</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}</td>
                      <td>{r.trigger}</td>
                      <td>{formatTime(r.started_at)}</td>
                      <td>{formatTime(r.finished_at)}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[r.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[r.status] || r.status}
                        </span>
                      </td>
                      <td>
                        {r.records_loaded}/{r.records_read}
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