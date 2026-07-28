import { useEffect, useState } from "react";
import { AlertCircle, Download, Eye, Filter, RotateCcw, Sparkles, X } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { exportAiAuditReport, getAiAuditLogByTraceId, listAiAuditLogs } from "../api/aiAuditLogs.js";

const EMPTY_FILTERS = { userId: "", timeFrom: "", timeTo: "" };

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function AiAuditLogPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [period, setPeriod] = useState("WEEK");
  const [exporting, setExporting] = useState(false);

  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  async function reload(activeFilters = filters) {
    setLoading(true);
    try {
      const data = await listAiAuditLogs({
        userId: activeFilters.userId,
        timeFrom: activeFilters.timeFrom,
        timeTo: activeFilters.timeTo,
      });
      setLogs(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload(EMPTY_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(e) {
    e.preventDefault();
    reload(filters);
  }

  function handleResetFilters() {
    setFilters(EMPTY_FILTERS);
    reload(EMPTY_FILTERS);
  }

  async function handleViewDetail(traceId) {
    setDetailLoading(true);
    try {
      const data = await getAiAuditLogByTraceId(traceId);
      setSelected(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportAiAuditReport({
        period,
        timeFrom: filters.timeFrom,
        timeTo: filters.timeTo,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "bao-cao-ai-audit.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setExporting(false);
    }
  }

  return (
    <AppLayout
      title="Quản trị AI Audit Log"
      subtitle="UC-10 — Xem AI query theo thời gian/trace_id/user_id; xuất báo cáo AI Audit định kỳ tuần/tháng (PDF)."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>
            <Filter size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Bộ lọc
          </h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleFilterSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="filter-user-id">Người dùng (user_id)</label>
                <input
                  id="filter-user-id"
                  placeholder="vd: canbo1"
                  value={filters.userId}
                  onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="filter-time-from">Từ thời gian</label>
                <input
                  id="filter-time-from"
                  type="datetime-local"
                  value={filters.timeFrom}
                  onChange={(e) => setFilters({ ...filters, timeFrom: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="filter-time-to">Đến thời gian</label>
                <input
                  id="filter-time-to"
                  type="datetime-local"
                  value={filters.timeTo}
                  onChange={(e) => setFilters({ ...filters, timeTo: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="export-period">Kỳ báo cáo</label>
                <select id="export-period" value={period} onChange={(e) => setPeriod(e.target.value)}>
                  <option value="WEEK">Tuần</option>
                  <option value="MONTH">Tháng</option>
                </select>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  <Filter size={15} />
                  Lọc
                </button>
                <button type="button" className="btn" onClick={handleResetFilters} disabled={loading}>
                  <RotateCcw size={15} />
                  Xoá lọc
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleExport}
                  disabled={exporting}
                  title="Xuất báo cáo AI Audit định kỳ theo kỳ + khoảng thời gian đang lọc"
                >
                  <Download size={15} />
                  {exporting ? "Đang xuất..." : "Xuất báo cáo AI Audit"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {selected && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div
            className="card-header"
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
          >
            <h2>
              <Sparkles size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
              Chi tiết phiên hỏi-đáp — trace_id: {selected.trace_id}
            </h2>
            <button className="icon-btn" title="Đóng" onClick={() => setSelected(null)}>
              <X size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label>Người dùng</label>
                <div>{selected.username}</div>
              </div>
              <div className="field">
                <label>Mô hình</label>
                <div>{selected.model || "—"}</div>
              </div>
              <div className="field">
                <label>Phiên bản mẫu (prompt_version)</label>
                <div>{selected.prompt_version || "—"}</div>
              </div>
              <div className="field">
                <label>Thời gian</label>
                <div>{formatTime(selected.created_at)}</div>
              </div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <label>Câu hỏi (prompt)</label>
              <div style={{ whiteSpace: "pre-wrap" }}>{selected.prompt}</div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <label>Phản hồi (response)</label>
              <div style={{ whiteSpace: "pre-wrap" }}>{selected.response || "—"}</div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <label>Nguồn dẫn (sources)</label>
              <div>
                {selected.sources && selected.sources.length > 0
                  ? selected.sources.join(", ")
                  : "—"}
              </div>
            </div>
            <div className="field">
              <label>Ảnh chụp quyền (permission_snapshot)</label>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
                {JSON.stringify(selected.permission_snapshot || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>
            <Sparkles size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            AI Audit Log ({logs.length})
          </h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : logs.length === 0 ? (
            <div className="empty-state">Không có phiên hỏi-đáp AI nào phù hợp bộ lọc.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Người dùng</th>
                  <th>Mô hình</th>
                  <th>Trace ID</th>
                  <th>Số nguồn dẫn</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatTime(entry.created_at)}</td>
                    <td>{entry.username}</td>
                    <td>{entry.model || "—"}</td>
                    <td>{entry.trace_id}</td>
                    <td>{(entry.sources || []).length}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-btn"
                          title="Xem toàn bộ chuỗi hỏi-đáp"
                          disabled={detailLoading}
                          onClick={() => handleViewDetail(entry.trace_id)}
                        >
                          <Eye size={15} />
                        </button>
                      </div>
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