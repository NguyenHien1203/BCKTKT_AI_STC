import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw, Search, Send } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { callSearchApi, listSearchApiAuditLogs } from "../../api/searchApi.js";

const STATUS_LABEL = { SUCCESS: "Thành công", DENIED: "Từ chối", ERROR: "Lỗi" };
const STATUS_BADGE_CLASS = {
  SUCCESS: "badge-success",
  DENIED: "badge-warning",
  ERROR: "badge-danger",
};
const SECURITY_LEVEL_LABEL = {
  PUBLIC: "Công khai",
  NOI_BO: "Nội bộ",
  MAT: "Mật",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_QUERY_FORM = {
  apiKey: "",
  query: "quyết toán ngân sách 2026",
  topK: 10,
  userDonViCode: "",
  userSecurityLevel: "PUBLIC",
};

export default function SearchApiPage() {
  // ---------- Bước 1+2+3 — QLVBĐH gọi Search API ----------
  const [queryForm, setQueryForm] = useState(EMPTY_QUERY_FORM);
  const [queryResult, setQueryResult] = useState(null);

  // ---------- Tra cứu audit.audit_log ----------
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
      const data = await listSearchApiAuditLogs({
        apiType: "SEARCH",
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

  // Bước 1+2+3 — QLVBĐH gọi Search API qua Cổng API: hệ thống tìm kiếm
  // vector + BM25, lọc theo quyền của khoá rồi lọc tiếp theo phạm vi của
  // người dùng đến từ QLVBĐH, trả kết quả kèm dẫn nguồn.
  async function handleCallSearchApi(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    setQueryResult(null);
    try {
      const data = await callSearchApi(queryForm.apiKey, {
        query: queryForm.query,
        topK: Number(queryForm.topK) || 10,
        userDonViCode: queryForm.userDonViCode,
        userSecurityLevel: queryForm.userSecurityLevel,
      });
      setQueryResult(data);
      setInfo(`Tìm kiếm thành công — nhận ${data.result_count} kết quả.`);
      await loadAuditLogs();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail?.message || "Gọi Search API thất bại");
      await loadAuditLogs();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Cung cấp Search API cho QLVBĐH/cổng nội bộ"
      subtitle="UC-066 — QLVBĐH gọi Search API, hệ thống tìm kiếm vector + BM25; lọc theo quyền của khoá API rồi lọc tiếp theo phạm vi của người dùng đến từ QLVBĐH; trả kết quả kèm dẫn nguồn, hệ thống phản hồi JSON."
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

      {/* ---------- Bước 1+2+3 — Gọi Search API ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>
            <Search size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
            Gọi Search API (vector + BM25)
          </h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleCallSearchApi} className="form-grid">
            <div className="field">
              <label htmlFor="search-api-key">Khoá API (X-API-Key)</label>
              <input
                id="search-api-key"
                value={queryForm.apiKey}
                onChange={(e) => setQueryForm({ ...queryForm, apiKey: e.target.value })}
                placeholder="vd: gw_..."
              />
            </div>
            <div className="field">
              <label htmlFor="search-query">Từ khoá tìm kiếm (query)</label>
              <input
                id="search-query"
                value={queryForm.query}
                onChange={(e) => setQueryForm({ ...queryForm, query: e.target.value })}
                placeholder="vd: quyết toán ngân sách 2026"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="search-top-k">Số kết quả tối đa (top_k)</label>
              <input
                id="search-top-k"
                type="number"
                min={1}
                max={50}
                value={queryForm.topK}
                onChange={(e) => setQueryForm({ ...queryForm, topK: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="search-user-security-level">Mức bảo mật người dùng</label>
              <select
                id="search-user-security-level"
                value={queryForm.userSecurityLevel}
                onChange={(e) =>
                  setQueryForm({ ...queryForm, userSecurityLevel: e.target.value })
                }
              >
                <option value="PUBLIC">Công khai (PUBLIC)</option>
                <option value="NOI_BO">Nội bộ (NOI_BO)</option>
                <option value="MAT">Mật (MAT)</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="search-user-don-vi">Đơn vị người dùng (phạm vi)</label>
              <input
                id="search-user-don-vi"
                value={queryForm.userDonViCode}
                onChange={(e) => setQueryForm({ ...queryForm, userDonViCode: e.target.value })}
                placeholder="vd: Sở Tài chính (để trống = không giới hạn đơn vị)"
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                <Send size={14} style={{ marginRight: 6 }} />
                Tìm kiếm
              </button>
            </div>
          </form>

          {queryResult && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Từ khoá <strong>{queryResult.query}</strong> — {queryResult.result_count} kết quả.
              </p>
              {queryResult.results.length > 0 && (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mã văn bản</th>
                      <th>Tiêu đề / trích đoạn</th>
                      <th>Điểm (vector / BM25 / tổng)</th>
                      <th>Đơn vị</th>
                      <th>Mức bảo mật</th>
                      <th>Dẫn nguồn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queryResult.results.map((item) => (
                      <tr key={item.doc_code}>
                        <td>{item.doc_code}</td>
                        <td>
                          <div>{item.title}</div>
                          <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                            {item.snippet}
                          </div>
                        </td>
                        <td>
                          {item.vector_score} / {item.bm25_score} / <strong>{item.score}</strong>
                        </td>
                        <td>{item.don_vi_code || "Dùng chung"}</td>
                        <td>{SECURITY_LEVEL_LABEL[item.security_level] || item.security_level}</td>
                        <td>
                          <a href={item.source.source_url} target="_blank" rel="noreferrer">
                            {item.source.source_system}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ---------- Tra cứu audit.audit_log ---------- */}
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
              <label htmlFor="search-audit-consumer-filter">Đơn vị khai thác</label>
              <input
                id="search-audit-consumer-filter"
                value={consumerFilter}
                onChange={(e) => setConsumerFilter(e.target.value)}
                placeholder="vd: QLVBDH-01"
              />
            </div>
            <div className="field">
              <label htmlFor="search-audit-status-filter">Trạng thái</label>
              <select
                id="search-audit-status-filter"
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
                  <th>Số kết quả</th>
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
