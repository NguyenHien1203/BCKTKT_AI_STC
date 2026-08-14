import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Gauge, RefreshCw, Zap } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  SERVICE_TIER_CODES,
  THROTTLE_POLICIES,
  configureBurstPolicy,
  configureRateLimit,
  createServiceTier,
  getBurstPolicy,
  getRateLimit,
  listServiceTiers,
  updateServiceTier,
} from "../../api/rateLimits.js";

const TIER_LABEL = {
  FREE: "Miễn phí",
  STANDARD: "Tiêu chuẩn",
  PREMIUM: "Cao cấp",
};

const THROTTLE_LABEL = {
  REJECT: "Từ chối (Reject)",
  QUEUE: "Xếp hàng (Queue)",
  DELAY: "Trì hoãn (Delay)",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_TIER_FORM = { code: "FREE", name: "", description: "" };
const EMPTY_RATE_LIMIT_FORM = { requests_per_second: "", requests_per_day: "" };
const EMPTY_BURST_FORM = { burst_limit: "", window_seconds: "", throttle_policy: "REJECT" };

export default function RateLimitsPage() {
  const [tiers, setTiers] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [rateLimit, setRateLimit] = useState(null);
  const [burstPolicy, setBurstPolicy] = useState(null);

  const [tierForm, setTierForm] = useState(EMPTY_TIER_FORM);
  const [rateLimitForm, setRateLimitForm] = useState(EMPTY_RATE_LIMIT_FORM);
  const [burstForm, setBurstForm] = useState(EMPTY_BURST_FORM);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedTier = tiers.find((t) => t.id === selectedId) || null;

  // Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
  async function loadTiers(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listServiceTiers();
      const safeData = Array.isArray(data) ? data : [];
      setTiers(safeData);
      if (!keepSelection || !safeData.some((t) => t.id === selectedId)) {
        setSelectedId(safeData.length > 0 ? safeData[0].id : null);
      }
      setError(Array.isArray(data) ? null : "Không tải được danh sách gói dịch vụ (phản hồi không hợp lệ)");
    } catch (err) {
      setTiers([]);
      setError(err?.response?.data?.detail?.message || "Không tải được danh sách gói dịch vụ");
    } finally {
      setLoading(false);
    }
  }

  async function loadRateLimit(tierId) {
    if (!tierId) {
      setRateLimit(null);
      return;
    }
    try {
      const data = await getRateLimit(tierId);
      setRateLimit(data);
      setRateLimitForm({
        requests_per_second: data.requests_per_second,
        requests_per_day: data.requests_per_day,
      });
    } catch {
      setRateLimit(null);
      setRateLimitForm(EMPTY_RATE_LIMIT_FORM);
    }
  }

  async function loadBurstPolicy(tierId) {
    if (!tierId) {
      setBurstPolicy(null);
      return;
    }
    try {
      const data = await getBurstPolicy(tierId);
      setBurstPolicy(data);
      setBurstForm({
        burst_limit: data.burst_limit,
        window_seconds: data.window_seconds,
        throttle_policy: data.throttle_policy,
      });
    } catch {
      setBurstPolicy(null);
      setBurstForm(EMPTY_BURST_FORM);
    }
  }

  useEffect(() => {
    loadTiers(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadRateLimit(selectedId);
    loadBurstPolicy(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  // Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
  async function handleCreateTier(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    try {
      const created = await createServiceTier(tierForm);
      setInfo(`Đã lưu cấu hình gói "${created.name}" (${TIER_LABEL[created.code] || created.code}).`);
      setTierForm(EMPTY_TIER_FORM);
      await loadTiers(false);
      setSelectedId(created.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cấu hình gói dịch vụ thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(tier) {
    clearMessages();
    setSubmitting(true);
    try {
      await updateServiceTier(tier.id, {
        name: tier.name,
        description: tier.description,
        is_active: !tier.is_active,
      });
      setInfo(`Đã ${tier.is_active ? "tắt" : "bật"} gói "${tier.name}".`);
      await loadTiers(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cập nhật gói dịch vụ thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) -> hệ
  // thống áp dụng tại Cổng API.
  async function handleConfigureRateLimit(e) {
    e.preventDefault();
    if (!selectedTier) return;
    clearMessages();
    setSubmitting(true);
    try {
      const data = await configureRateLimit(selectedTier.id, {
        requestsPerSecond: Number(rateLimitForm.requests_per_second),
        requestsPerDay: Number(rateLimitForm.requests_per_day),
      });
      setRateLimit(data);
      setInfo(`Đã áp dụng giới hạn tần suất tại Cổng API cho gói "${selectedTier.name}".`);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cấu hình giới hạn tần suất thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ thống
  // lưu.
  async function handleConfigureBurst(e) {
    e.preventDefault();
    if (!selectedTier) return;
    clearMessages();
    setSubmitting(true);
    try {
      const data = await configureBurstPolicy(selectedTier.id, {
        burstLimit: Number(burstForm.burst_limit),
        windowSeconds: Number(burstForm.window_seconds),
        throttlePolicy: burstForm.throttle_policy,
      });
      setBurstPolicy(data);
      setInfo(`Đã lưu chính sách giới hạn đột biến + điều tiết cho gói "${selectedTier.name}".`);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cấu hình giới hạn đột biến thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý giới hạn tần suất + gói dịch vụ"
      subtitle="UC-060 — Cấu hình gói (miễn phí/tiêu chuẩn/cao cấp); cấu hình giới hạn tần suất theo gói (req/giây, req/ngày) áp dụng tại Cổng API; cấu hình giới hạn đột biến + chính sách điều tiết."
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

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
        {/* ---------- Cột trái: danh sách gói dịch vụ ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Danh sách gói dịch vụ</h2>
            <button className="icon-btn" title="Tải lại" onClick={() => loadTiers(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            {loading && <p>Đang tải…</p>}
            {!loading && tiers.length === 0 && (
              <div className="empty-state">Chưa có gói dịch vụ nào.</div>
            )}

            {!loading && tiers.length > 0 && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Gói dịch vụ</th>
                    <th>Mô tả</th>
                    <th>Trạng thái</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tiers.map((t) => (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedId(t.id)}
                      style={{
                        cursor: "pointer",
                        background:
                          t.id === selectedId ? "var(--color-primary-soft)" : undefined,
                      }}
                    >
                      <td>
                        <div>
                          <strong>{t.name}</strong>
                        </div>
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {TIER_LABEL[t.code] || t.code} · {t.code}
                        </div>
                      </td>
                      <td style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                        {t.description || "—"}
                      </td>
                      <td>
                        <span className={`badge ${t.is_active ? "badge-success" : "badge-neutral"}`}>
                          {t.is_active ? "Đang áp dụng" : "Đã tắt"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className={t.is_active ? "btn btn-danger-ghost" : "btn btn-secondary"}
                            disabled={submitting}
                            onClick={(ev) => {
                              ev.stopPropagation();
                              handleToggleActive(t);
                            }}
                          >
                            {t.is_active ? "Tắt" : "Bật"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <h3 style={{ marginTop: 24, marginBottom: 12 }}>Cấu hình gói mới</h3>
            <form onSubmit={handleCreateTier} className="form-grid">
              <div className="field">
                <label htmlFor="tier-code">Loại gói</label>
                <select
                  id="tier-code"
                  value={tierForm.code}
                  onChange={(e) => setTierForm((f) => ({ ...f, code: e.target.value }))}
                >
                  {SERVICE_TIER_CODES.map((code) => (
                    <option key={code} value={code}>
                      {TIER_LABEL[code]} ({code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="tier-name">Tên gói</label>
                <input
                  id="tier-name"
                  required
                  value={tierForm.name}
                  onChange={(e) => setTierForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="vd: Gói Tiêu chuẩn"
                />
              </div>
              <div className="field" style={{ gridColumn: "1 / -1" }}>
                <label htmlFor="tier-description">Mô tả</label>
                <textarea
                  id="tier-description"
                  rows={2}
                  value={tierForm.description}
                  onChange={(e) => setTierForm((f) => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  Lưu cấu hình gói
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* ---------- Cột phải: giới hạn tần suất + burst của gói đang chọn ---------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2>
                <Gauge size={16} style={{ marginRight: 6 }} />
                Giới hạn tần suất (Cổng API)
              </h2>
            </div>
            <div className="card-body">
              {!selectedTier && <p>Chọn 1 gói dịch vụ ở bảng bên trái.</p>}
              {selectedTier && (
                <>
                  {rateLimit && (
                    <p style={{ fontSize: 12, opacity: 0.75, marginBottom: 8 }}>
                      Áp dụng tại Cổng API lúc: {formatTime(rateLimit.applied_at)}
                    </p>
                  )}
                  <form onSubmit={handleConfigureRateLimit} className="form-grid">
                    <div className="field">
                      <label htmlFor="rps">Giới hạn (req/giây)</label>
                      <input
                        id="rps"
                        type="number"
                        min={1}
                        required
                        value={rateLimitForm.requests_per_second}
                        onChange={(e) =>
                          setRateLimitForm((f) => ({ ...f, requests_per_second: e.target.value }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rpd">Giới hạn (req/ngày)</label>
                      <input
                        id="rpd"
                        type="number"
                        min={1}
                        required
                        value={rateLimitForm.requests_per_day}
                        onChange={(e) =>
                          setRateLimitForm((f) => ({ ...f, requests_per_day: e.target.value }))
                        }
                      />
                    </div>
                    <div style={{ gridColumn: "1 / -1" }}>
                      <button className="btn" type="submit" disabled={submitting}>
                        Áp dụng tại Cổng API
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>
                <Zap size={16} style={{ marginRight: 6 }} />
                Giới hạn đột biến + điều tiết
              </h2>
            </div>
            <div className="card-body">
              {!selectedTier && <p>Chọn 1 gói dịch vụ ở bảng bên trái.</p>}
              {selectedTier && (
                <>
                  {burstPolicy && (
                    <p style={{ fontSize: 12, opacity: 0.75, marginBottom: 8 }}>
                      Chính sách hiện tại: {THROTTLE_LABEL[burstPolicy.throttle_policy]}
                    </p>
                  )}
                  <form onSubmit={handleConfigureBurst} className="form-grid">
                    <div className="field">
                      <label htmlFor="burst-limit">Giới hạn đột biến (số request)</label>
                      <input
                        id="burst-limit"
                        type="number"
                        min={1}
                        required
                        value={burstForm.burst_limit}
                        onChange={(e) => setBurstForm((f) => ({ ...f, burst_limit: e.target.value }))}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="window-seconds">Cửa sổ thời gian (giây)</label>
                      <input
                        id="window-seconds"
                        type="number"
                        min={1}
                        required
                        value={burstForm.window_seconds}
                        onChange={(e) =>
                          setBurstForm((f) => ({ ...f, window_seconds: e.target.value }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="throttle-policy">Chính sách điều tiết</label>
                      <select
                        id="throttle-policy"
                        value={burstForm.throttle_policy}
                        onChange={(e) =>
                          setBurstForm((f) => ({ ...f, throttle_policy: e.target.value }))
                        }
                      >
                        {THROTTLE_POLICIES.map((p) => (
                          <option key={p} value={p}>
                            {THROTTLE_LABEL[p]}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={{ gridColumn: "1 / -1" }}>
                      <button className="btn" type="submit" disabled={submitting}>
                        Lưu chính sách điều tiết
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}