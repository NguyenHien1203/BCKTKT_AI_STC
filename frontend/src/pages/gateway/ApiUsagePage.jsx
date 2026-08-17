import { useEffect, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, RefreshCw, Send } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  getApiUsageConsumers,
  getApiUsageDashboard,
  listAnomalyAlerts,
  simulateAlertmanagerWebhook,
} from "../../api/apiUsage.js";

const SEVERITY_LABEL = { INFO: "Thông tin", WARNING: "Cảnh báo", CRITICAL: "Nghiêm trọng" };
const SEVERITY_COLOR = {
  INFO: "var(--color-primary)",
  WARNING: "#b45309",
  CRITICAL: "#b91c1c",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_ALERT_FORM = {
  alertname: "HighErrorRate",
  severity: "WARNING",
  consumer_code: "",
  summary: "Tỉ lệ lỗi API vượt ngưỡng",
  description: "",
};

export default function ApiUsagePage() {
  // ---------- Bước 1: bảng điều khiển tổng quan ----------
  const [dashboard, setDashboard] = useState(null);
  const [windowMinutes, setWindowMinutes] = useState(60);

  // ---------- Bước 2: chi tiết theo đơn vị khai thác ----------
  const [consumers, setConsumers] = useState([]);
  const [consumerFilter, setConsumerFilter] = useState("");

  // ---------- Bước 3: cảnh báo bất thường ----------
  const [alerts, setAlerts] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [alertForm, setAlertForm] = useState(EMPTY_ALERT_FORM);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  async function loadDashboard() {
    setLoading(true);
    try {
      const data = await getApiUsageDashboard({ windowMinutes });
      setDashboard(data);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Không tải được bảng điều khiển từ Prometheus");
    } finally {
      setLoading(false);
    }
  }

  async function loadConsumers() {
    try {
      const data = await getApiUsageConsumers({
        windowMinutes,
        consumerCode: consumerFilter || null,
      });
      setConsumers(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Không tải được chi tiết theo đơn vị khai thác");
    }
  }

  async function loadAlerts() {
    try {
      const data = await listAnomalyAlerts({ status: statusFilter || null });
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Không tải được lịch sử cảnh báo");
    }
  }

  useEffect(() => {
    loadDashboard();
    loadConsumers();
    loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleReloadAll(e) {
    e?.preventDefault?.();
    clearMessages();
    await Promise.all([loadDashboard(), loadConsumers(), loadAlerts()]);
  }

  async function handleFilterConsumer(e) {
    e.preventDefault();
    clearMessages();
    await loadConsumers();
  }

  async function handleFilterAlerts(e) {
    e.preventDefault();
    clearMessages();
    await loadAlerts();
  }

  // Mô phỏng Alertmanager gửi 1 cảnh báo qua webhook — hữu ích để demo/
  // kiểm thử khi chưa cấu hình Alertmanager thật trỏ về
  // `POST /api/api-gateway/alerts/webhook`.
  async function handleSimulateAlert(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    try {
      const fingerprint = `demo-${Date.now()}`;
      await simulateAlertmanagerWebhook({
        receiver: "api-gateway-webhook",
        status: "firing",
        alerts: [
          {
            status: "firing",
            labels: {
              alertname: alertForm.alertname,
              severity: alertForm.severity.toLowerCase(),
              ...(alertForm.consumer_code ? { consumer_code: alertForm.consumer_code } : {}),
            },
            annotations: {
              summary: alertForm.summary,
              description: alertForm.description,
            },
            startsAt: new Date().toISOString(),
            endsAt: "0001-01-01T00:00:00Z",
            fingerprint,
          },
        ],
      });
      setInfo("Đã mô phỏng Alertmanager gửi 1 cảnh báo bất thường.");
      await loadAlerts();
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Gửi cảnh báo mô phỏng thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  const summary = dashboard?.summary;
  const series = dashboard?.series || [];
  const maxRps = Math.max(1, ...series.map((p) => p.requests_per_second));

  return (
    <AppLayout
      title="Theo dõi mức sử dụng API + chỉ số"
      subtitle="UC-061 — Xem bảng điều khiển mức sử dụng API (req/giây, độ trễ, tỉ lệ lỗi) từ Prometheus; xem chi tiết theo đơn vị khai thác; cảnh báo khi API có bất thường (Alertmanager gửi cảnh báo)."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          <CheckCircle2 size={16} />
          <span>{info}</span>
        </div>
      )}

      {/* ---------- Bước 1 — Bảng điều khiển mức sử dụng API ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bảng điều khiển mức sử dụng API (từ Prometheus)</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={windowMinutes} onChange={(e) => setWindowMinutes(Number(e.target.value))}>
              <option value={15}>15 phút gần nhất</option>
              <option value={60}>1 giờ gần nhất</option>
              <option value={360}>6 giờ gần nhất</option>
              <option value={1440}>24 giờ gần nhất</option>
            </select>
            <button className="icon-btn" title="Tải lại" onClick={handleReloadAll}>
              <RefreshCw size={15} />
            </button>
          </div>
        </div>
        <div className="card-body">
          {loading && <p>Đang tải…</p>}
          {!loading && summary && (
            <>
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: "#666" }}>Req/giây</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{summary.requests_per_second}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#666" }}>Độ trễ trung bình (ms)</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{summary.avg_latency_ms}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#666" }}>Tỉ lệ lỗi (%)</div>
                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 600,
                      color: summary.error_rate_percent > 3 ? "#cf222e" : "#1a7f37",
                    }}
                  >
                    {summary.error_rate_percent}%
                  </div>
                </div>
              </div>

              {/* Biểu đồ req/giây theo thời gian — SVG thuần, không thêm thư viện chart */}
              <svg viewBox="0 0 600 120" width="100%" height="120" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="var(--color-primary)"
                  strokeWidth="2"
                  points={series
                    .map((p, i) => {
                      const x = (i / Math.max(1, series.length - 1)) * 600;
                      const y = 110 - (p.requests_per_second / maxRps) * 100;
                      return `${x},${y}`;
                    })
                    .join(" ")}
                />
              </svg>
              <p style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                Xu hướng req/giây trong {windowMinutes} phút gần nhất (tổng {summary.total_requests} request).
              </p>
            </>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* ---------- Bước 2 — Chi tiết theo đơn vị khai thác ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Chi tiết theo đơn vị khai thác</h2>
          </div>
          <div className="card-body">
            <form onSubmit={handleFilterConsumer} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <input
                placeholder="Lọc theo mã đơn vị khai thác (vd QLVBDH)"
                value={consumerFilter}
                onChange={(e) => setConsumerFilter(e.target.value)}
              />
              <button type="submit" className="btn btn-secondary">
                Lọc
              </button>
            </form>
            {consumers.length === 0 && <div className="empty-state">Chưa có dữ liệu.</div>}
            {consumers.length > 0 && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Đơn vị khai thác</th>
                    <th>Req/giây</th>
                    <th>Độ trễ (ms)</th>
                    <th>Tỉ lệ lỗi (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {consumers.map((c) => (
                    <tr key={c.consumer_code}>
                      <td>{c.consumer_code}</td>
                      <td>{c.requests_per_second}</td>
                      <td>{c.avg_latency_ms}</td>
                      <td>{c.error_rate_percent}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Bước 3 — Cảnh báo khi API có bất thường ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Cảnh báo bất thường (Alertmanager)</h2>
          </div>
          <div className="card-body">
            <form onSubmit={handleFilterAlerts} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">Tất cả trạng thái</option>
                <option value="FIRING">Đang xảy ra (FIRING)</option>
                <option value="RESOLVED">Đã xử lý (RESOLVED)</option>
              </select>
              <button type="submit" className="btn btn-secondary">
                Lọc
              </button>
            </form>

            {alerts.length === 0 && <div className="empty-state">Chưa có cảnh báo nào.</div>}
            {alerts.length > 0 && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cảnh báo</th>
                    <th>Mức độ</th>
                    <th>Trạng thái</th>
                    <th>Đơn vị</th>
                    <th>Nhận lúc</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{a.alert_name}</div>
                        <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{a.summary}</div>
                      </td>
                      <td>
                        <span style={{ color: SEVERITY_COLOR[a.severity], fontWeight: 600 }}>
                          <AlertTriangle size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />
                          {SEVERITY_LABEL[a.severity] || a.severity}
                        </span>
                      </td>
                      <td>{a.status === "FIRING" ? "Đang xảy ra" : "Đã xử lý"}</td>
                      <td>{a.consumer_code || "—"}</td>
                      <td>{formatTime(a.received_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <hr style={{ margin: "16px 0" }} />
            <h3 style={{ fontSize: 14, marginBottom: 8 }}>Mô phỏng Alertmanager gửi cảnh báo (demo/kiểm thử)</h3>
            <form onSubmit={handleSimulateAlert} style={{ display: "grid", gap: 8 }}>
              <input
                placeholder="Tên cảnh báo (alertname)"
                value={alertForm.alertname}
                onChange={(e) => setAlertForm({ ...alertForm, alertname: e.target.value })}
                required
              />
              <select
                value={alertForm.severity}
                onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}
              >
                <option value="INFO">Thông tin</option>
                <option value="WARNING">Cảnh báo</option>
                <option value="CRITICAL">Nghiêm trọng</option>
              </select>
              <input
                placeholder="Mã đơn vị khai thác (tuỳ chọn)"
                value={alertForm.consumer_code}
                onChange={(e) => setAlertForm({ ...alertForm, consumer_code: e.target.value })}
              />
              <input
                placeholder="Tóm tắt"
                value={alertForm.summary}
                onChange={(e) => setAlertForm({ ...alertForm, summary: e.target.value })}
              />
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                <Send size={14} style={{ marginRight: 6 }} />
                Gửi cảnh báo mô phỏng
              </button>
            </form>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}