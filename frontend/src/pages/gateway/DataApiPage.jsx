import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Database, RefreshCw, Send } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { callDataApi, listDataApiAuditLogs } from "../../api/dataApi.js";

const STATUS_LABEL = { SUCCESS: "Thành công", DENIED: "Từ chối", ERROR: "Lỗi" };
const STATUS_BADGE_CLASS = {
  SUCCESS: "badge-success",
  DENIED: "badge-warning",
  ERROR: "badge-danger",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_QUERY_FORM = {
  apiKey: "",
  datasetCode: "NGAN_SACH_TONG_HOP",
  filtersText: "{}",
};

export default function DataApiPage() {
  // ---------- Bước 1+2 — IOC gọi Data API tổng hợp ----------
  const [queryForm, setQueryForm] = useState(EMPTY_QUERY_FORM);
  const [queryResult, setQueryResult] = useState(null);

  // ---------- Bước 3 — Tra cứu audit.audit_log ----------
  const [auditLogs, setAuditLogs] = useState([]);
  const [consumerFilter, setConsumerFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  async function loadAuditLogs() {
    setLoading(true);
    try {
      const data = await listDataApiAuditLogs({
        apiType: "DATA",
        consumerCode: consumerFilter || null,
        status: statusFilter || null,
      });
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Không tải được nhật ký audit.audit_log");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAuditLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleFilterAuditLogs(e) {
    e.preventDefault();
    clearMessages();
    await loadAuditLogs();
  }

  // Bước 1+2 — gọi Data API tổng hợp qua Cổng API (khoá API + phạm vi +
  // giới hạn tần suất được kiểm tra tại `POST /data-api/query`).
  async function handleCallDataApi(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    setQueryResult(null);
    try {
      let filters = {};
      if (queryForm.filtersText.trim()) {
        try {
          filters = JSON.parse(queryForm.filtersText);
        } catch {
          setError('Bộ lọc phải là JSON hợp lệ, ví dụ {"nam": 2026}');
          setSubmitting(false);
          return;
        }
      }
      const data = await callDataApi(queryForm.apiKey, {
        datasetCode: queryForm.datasetCode,
        filters,
      });
      setQueryResult(data);
      setInfo(`Gọi Data API thành công — nhận ${data.row_count} dòng.`);
      await loadAuditLogs();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail?.message || "Gọi Data API thất bại");
      await loadAuditLogs();
    } finally {
      setSubmitting(false);
    }
  }

  const resultColumns = queryResult?.rows?.length > 0 ? Object.keys(queryResult.rows[0]) : [];

  return (
    <AppLayout
      title="Cung cấp Data API cho IOC"
      subtitle="UC-064 — IOC gọi Data API tổng hợp, hệ thống trả dữ liệu qua Lớp ngữ nghĩa; Cổng API kiểm tra khoá API + phạm vi + giới hạn tần suất; ghi nhật ký lời gọi API vào audit.audit_log."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{info}</span>
        </div>
      )}

      {/* ---------- Bước 1+2 — Gọi Data API tổng hợp ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>
            <Database size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
            Gọi Data API tổng hợp (qua Lớp ngữ nghĩa)
          </h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleCallDataApi} className="form-grid">
            <div className="field">
              <label htmlFor="data-api-key">Khoá API (X-API-Key)</label>
              <input
                id="data-api-key"
                value={queryForm.apiKey}
                onChange={(e) => setQueryForm({ ...queryForm, apiKey: e.target.value })}
                placeholder="vd: gw_..."
              />
            </div>
            <div className="field">
              <label htmlFor="dataset-code">Mã bộ dữ liệu (dataset_code)</label>
              <input
                id="dataset-code"
                value={queryForm.datasetCode}
                onChange={(e) => setQueryForm({ ...queryForm, datasetCode: e.target.value })}
                placeholder="vd: NGAN_SACH_TONG_HOP"
                required
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label htmlFor="dataset-filters">Bộ lọc (JSON)</label>
              <textarea
                id="dataset-filters"
                rows={3}
                value={queryForm.filtersText}
                onChange={(e) => setQueryForm({ ...queryForm, filtersText: e.target.value })}
                placeholder='vd: {"nam": 2026}'
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                <Send size={14} style={{ marginRight: 6 }} />
                Gọi Data API
              </button>
            </div>
          </form>

          {queryResult && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Bộ dữ liệu <strong>{queryResult.dataset_code}</strong> — {queryResult.row_count} dòng.
              </p>
              {resultColumns.length > 0 && (
                <table className="data-table">
                  <thead>
                    <tr>
                      {resultColumns.map((k) => (
                        <th key={k}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {queryResult.rows.map((row, i) => (
                      <tr key={i}>
                        {resultColumns.map((k) => (
                          <td key={k}>{String(row[k])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ---------- Bước 3 — Tra cứu audit.audit_log ---------- */}
      <div className="card">
        <div className="card-header">
          <h2>Nhật ký lời gọi API (audit.audit_log)</h2>
          <button className="icon-btn" title="Tải lại" onClick={loadAuditLogs}>
            <RefreshCw size={15} />
          </button>
        </div>
        <div className="card-body">
          <form onSubmit={handleFilterAuditLogs} className="form-grid" style={{ marginBottom: 12 }}>
            <div className="field">
              <label htmlFor="audit-consumer-filter">Đơn vị khai thác</label>
              <input
                id="audit-consumer-filter"
                value={consumerFilter}
                onChange={(e) => setConsumerFilter(e.target.value)}
                placeholder="vd: IOC-01"
              />
            </div>
            <div className="field">
              <label htmlFor="audit-status-filter">Trạng thái</label>
              <select
                id="audit-status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">-- Tất cả --</option>
                <option value="SUCCESS">Thành công</option>
                <option value="DENIED">Từ chối</option>
                <option value="ERROR">Lỗi</option>
              </select>
            </div>
            <div className="field">
              <label>&nbsp;</label>
              <button type="submit" className="btn btn-secondary">
                Lọc
              </button>
            </div>
          </form>

          {loading && <p>Đang tải…</p>}
          {!loading && auditLogs.length === 0 && <div className="empty-state">Chưa có lời gọi API nào.</div>}
          {!loading && auditLogs.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thời điểm</th>
                  <th>Đơn vị khai thác</th>
                  <th>Điểm cuối</th>
                  <th>Trạng thái</th>
                  <th>Số dòng</th>
                  <th>Lý do</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((l) => (
                  <tr key={l.id}>
                    <td>{formatTime(l.called_at)}</td>
                    <td>{l.consumer_code}</td>
                    <td>{l.endpoint_path}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE_CLASS[l.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[l.status] || l.status}
                      </span>
                    </td>
                    <td>{l.row_count ?? "—"}</td>
                    <td>{l.reason || "—"}</td>
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
