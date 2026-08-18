import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw, Send, Server } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { callLgspApi, listLgspAuditLogs } from "../../api/lgsp.js";

const STATUS_LABEL = { SUCCESS: "Thành công", DENIED: "Từ chối", ERROR: "Lỗi" };
const STATUS_BADGE_CLASS = {
  SUCCESS: "badge-success",
  DENIED: "badge-warning",
  ERROR: "badge-danger",
};

const RESPONSE_CODE_LABEL = {
  "00": "Thành công",
  E01: "Thiếu chứng thư mTLS",
  E02: "Chứng thư không hợp lệ / hết hạn",
  E03: "Chứng thư đã bị thu hồi",
  E04: "Yêu cầu không hợp lệ",
  E05: "Hệ thống thực thi thất bại",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function genRequestId() {
  return `REQ-${Date.now().toString(36).toUpperCase()}`;
}

const EMPTY_FORM = {
  certSerial: "",
  requestId: genRequestId(),
  serviceCode: "NGAN_SACH_TONG_HOP",
  payloadText: "{}",
};

export default function LgspApiPage() {
  // ---------- Bước 1+2 — Cổng LGSP chuyển tiếp yêu cầu / kiểm tra mTLS ----------
  const [form, setForm] = useState(EMPTY_FORM);
  const [envelope, setEnvelope] = useState(null);

  // ---------- Bước 3 — Tra cứu audit.audit_log (api_type=LGSP) ----------
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
      const data = await listLgspAuditLogs({
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

  // Bước 1+2+3 — gọi Cổng LGSP: hệ thống nhận -> kiểm tra chứng thư mTLS
  // -> thực thi -> LUÔN trả về phong bì phản hồi chuẩn LGSP.
  async function handleCallLgsp(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    setEnvelope(null);
    try {
      let payload = {};
      if (form.payloadText.trim()) {
        try {
          payload = JSON.parse(form.payloadText);
        } catch {
          setError('Payload phải là JSON hợp lệ, ví dụ {"nam": 2026}');
          setSubmitting(false);
          return;
        }
      }
      const data = await callLgspApi(form.certSerial, {
        requestId: form.requestId,
        serviceCode: form.serviceCode,
        payload,
      });
      setEnvelope(data);
      if (data.response_code === "00") {
        setInfo(`Gọi qua LGSP thành công — nhận ${data.data?.row_count ?? 0} dòng.`);
      } else {
        setError(`Cổng LGSP từ chối/lỗi [${data.response_code}]: ${data.response_message}`);
      }
      setForm((f) => ({ ...f, requestId: genRequestId() }));
      await loadAuditLogs();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail?.message || "Gọi qua Cổng LGSP thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  const resultColumns =
    envelope?.data?.rows?.length > 0 ? Object.keys(envelope.data.rows[0]) : [];

  return (
    <AppLayout
      title="Cung cấp API qua LGSP"
      subtitle="UC-065 — Cổng LGSP chuyển tiếp yêu cầu, hệ thống nhận; Cổng API kiểm tra chứng thư mTLS trước khi thực thi; hệ thống luôn trả phản hồi theo chuẩn LGSP (phong bì response_code)."
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

      {/* ---------- Bước 1+2 — Gửi yêu cầu qua Cổng LGSP ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>
            <Server size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
            Mô phỏng Cổng LGSP chuyển tiếp yêu cầu
          </h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleCallLgsp} className="form-grid">
            <div className="field">
              <label htmlFor="lgsp-cert-serial">Số hiệu chứng thư mTLS (X-Client-Cert-Serial)</label>
              <input
                id="lgsp-cert-serial"
                value={form.certSerial}
                onChange={(e) => setForm({ ...form, certSerial: e.target.value })}
                placeholder="vd: SN-0001 (đã đăng ký ở trang Quản lý chứng thư / mTLS)"
              />
            </div>
            <div className="field">
              <label htmlFor="lgsp-request-id">Mã giao dịch (request_id)</label>
              <input
                id="lgsp-request-id"
                value={form.requestId}
                onChange={(e) => setForm({ ...form, requestId: e.target.value })}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="lgsp-service-code">Mã dịch vụ (service_code)</label>
              <input
                id="lgsp-service-code"
                value={form.serviceCode}
                onChange={(e) => setForm({ ...form, serviceCode: e.target.value })}
                placeholder="vd: NGAN_SACH_TONG_HOP"
                required
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label htmlFor="lgsp-payload">Tham số (payload JSON)</label>
              <textarea
                id="lgsp-payload"
                rows={3}
                value={form.payloadText}
                onChange={(e) => setForm({ ...form, payloadText: e.target.value })}
                placeholder='vd: {"nam": 2026}'
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                <Send size={14} style={{ marginRight: 6 }} />
                Gửi yêu cầu qua LGSP
              </button>
            </div>
          </form>

          {envelope && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Phong bì phản hồi chuẩn LGSP — mã giao dịch{" "}
                <strong>{envelope.request_id}</strong>, mã kết quả{" "}
                <strong>{envelope.response_code}</strong> (
                {RESPONSE_CODE_LABEL[envelope.response_code] || envelope.response_code}), xử lý lúc{" "}
                {formatTime(envelope.processed_at)}.
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
                    {envelope.data.rows.map((row, i) => (
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

      {/* ---------- Bước 3 — Tra cứu audit.audit_log (api_type=LGSP) ---------- */}
      <div className="card">
        <div className="card-header">
          <h2>Nhật ký lời gọi qua LGSP (audit.audit_log)</h2>
          <button className="icon-btn" title="Tải lại" onClick={loadAuditLogs}>
            <RefreshCw size={15} />
          </button>
        </div>
        <div className="card-body">
          <form onSubmit={handleFilterAuditLogs} className="form-grid" style={{ marginBottom: 12 }}>
            <div className="field">
              <label htmlFor="lgsp-audit-consumer-filter">Đơn vị khai thác</label>
              <input
                id="lgsp-audit-consumer-filter"
                value={consumerFilter}
                onChange={(e) => setConsumerFilter(e.target.value)}
                placeholder="vd: LGSP-01"
              />
            </div>
            <div className="field">
              <label htmlFor="lgsp-audit-status-filter">Trạng thái</label>
              <select
                id="lgsp-audit-status-filter"
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
          {!loading && auditLogs.length === 0 && (
            <div className="empty-state">Chưa có lời gọi nào qua Cổng LGSP.</div>
          )}
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