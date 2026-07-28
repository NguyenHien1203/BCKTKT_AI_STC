import { useEffect, useState } from "react";
import { AlertCircle, Download, FileText, Filter, RotateCcw } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { exportSecurityReport, listAuditLogs } from "../api/auditLogs.js";

const EMPTY_FILTERS = { account: "", timeFrom: "", timeTo: "" };

const STATUS_LABEL = {
  SUCCESS: { label: "Thành công", className: "badge-success" },
  FAILURE: { label: "Thất bại", className: "badge-danger" },
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function AuditLogsPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  async function reload(activeFilters = filters) {
    setLoading(true);
    try {
      const data = await listAuditLogs({
        account: activeFilters.account,
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

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportSecurityReport({
        timeFrom: filters.timeFrom,
        timeTo: filters.timeTo,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "bao-cao-attt.pdf";
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
      title="Nhật ký truy cập và thao tác"
      subtitle="UC-09 — Xem toàn bộ nhật ký, lọc theo tài khoản/thời gian, xuất báo cáo ATTT định kỳ (PDF)."
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
                <label htmlFor="filter-account">Tài khoản</label>
                <input
                  id="filter-account"
                  placeholder="vd: admin"
                  value={filters.account}
                  onChange={(e) => setFilters({ ...filters, account: e.target.value })}
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
                  title="Xuất báo cáo ATTT (PDF) theo khoảng thời gian đang lọc"
                >
                  <Download size={15} />
                  {exporting ? "Đang xuất..." : "Xuất báo cáo ATTT (PDF)"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>
            <FileText size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Nhật ký ({logs.length})
          </h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : logs.length === 0 ? (
            <div className="empty-state">Không có bản ghi nhật ký nào phù hợp bộ lọc.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Tài khoản</th>
                  <th>Hành động</th>
                  <th>Đối tượng</th>
                  <th>Trạng thái</th>
                  <th>Địa chỉ IP</th>
                  <th>Chi tiết</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => {
                  const status = STATUS_LABEL[entry.status] || STATUS_LABEL.SUCCESS;
                  const resource = entry.resource_id
                    ? `${entry.resource_type}#${entry.resource_id}`
                    : entry.resource_type;
                  return (
                    <tr key={entry.id}>
                      <td>{formatTime(entry.created_at)}</td>
                      <td>{entry.username}</td>
                      <td>{entry.action}</td>
                      <td>{resource}</td>
                      <td>
                        <span className={`badge ${status.className}`}>{status.label}</span>
                      </td>
                      <td>{entry.ip_address || "—"}</td>
                      <td>{entry.detail || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  );
}