import { useEffect, useState } from "react";
import { BellRing, Trash2, Send } from "lucide-react";
import {
  listDashboardKpis,
  listDashboardAlertRules,
  configureDashboardAlertRule,
  activateDashboardAlertRule,
  deactivateDashboardAlertRule,
  listDashboardAlertChannels,
  addDashboardAlertChannel,
  deactivateDashboardAlertChannel,
  activateDashboardAlertChannel,
  deleteDashboardAlertChannel,
  evaluateDashboardAlertRule,
  listDashboardAlertLogs,
} from "../api/dashboards.js";

const OPERATOR_LABELS = {
  ">": "> (lớn hơn)",
  ">=": ">= (lớn hơn hoặc bằng)",
  "<": "< (nhỏ hơn)",
  "<=": "<= (nhỏ hơn hoặc bằng)",
};

const CHANNEL_LABELS = {
  EMAIL: "Email",
  SLACK: "Slack",
  WEBHOOK: "Webhook",
};

const currentYear = new Date().getFullYear();

/**
 * UC-052 — Đăng ký nhận cảnh báo dashboard.
 * Luồng: (1) Cấu hình ngưỡng cảnh báo trên KPI -> hệ thống lưu.
 *        (2) Chọn kênh nhận (email/Slack/Webhook) -> hệ thống lưu.
 *        (3) Khi vượt ngưỡng -> hệ thống gửi cảnh báo qua kênh đã chọn
 *            (nút "Đánh giá ngay" gọi thẳng bước 3 để kiểm tra cấu hình).
 */
export default function DashboardAlertsPanel({ dashboardId, userId }) {
  const [kpis, setKpis] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRuleId, setExpandedRuleId] = useState(null);
  const [ruleDetails, setRuleDetails] = useState({}); // ruleId -> { channels, logs }

  const [form, setForm] = useState({
    kpiCode: "",
    operator: ">",
    thresholdValue: "",
    year: currentYear,
    orgUnitCode: "",
    sector: "",
  });
  const [saving, setSaving] = useState(false);

  const [channelForm, setChannelForm] = useState({ channelType: "EMAIL", destination: "" });
  const [addingChannelToRule, setAddingChannelToRule] = useState(null);

  async function loadAll() {
    setLoading(true);
    try {
      const [kpiList, ruleList] = await Promise.all([
        listDashboardKpis(dashboardId, { onlyActive: true }),
        listDashboardAlertRules(dashboardId),
      ]);
      setKpis(kpiList);
      setRules(ruleList);
      if (!form.kpiCode && kpiList.length > 0) {
        setForm((f) => ({ ...f, kpiCode: kpiList[0].code }));
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboardId]);

  async function loadRuleDetail(ruleId) {
    try {
      const [channels, logs] = await Promise.all([
        listDashboardAlertChannels(dashboardId, ruleId),
        listDashboardAlertLogs(dashboardId, ruleId),
      ]);
      setRuleDetails((prev) => ({ ...prev, [ruleId]: { channels, logs } }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  function toggleExpand(ruleId) {
    const next = expandedRuleId === ruleId ? null : ruleId;
    setExpandedRuleId(next);
    if (next && !ruleDetails[next]) loadRuleDetail(next);
  }

  // ---------- Bước 1: Cấu hình ngưỡng cảnh báo trên KPI ----------
  async function submitRule(e) {
    e.preventDefault();
    if (!userId || !form.kpiCode || form.thresholdValue === "") return;
    setSaving(true);
    setError(null);
    try {
      await configureDashboardAlertRule(dashboardId, {
        kpiCode: form.kpiCode,
        userId,
        operator: form.operator,
        thresholdValue: Number(form.thresholdValue),
        year: Number(form.year),
        orgUnitCode: form.orgUnitCode,
        sector: form.sector,
      });
      setForm((f) => ({ ...f, thresholdValue: "", orgUnitCode: "", sector: "" }));
      await loadAll();
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleRuleActive(rule) {
    setError(null);
    try {
      if (rule.is_active) {
        await deactivateDashboardAlertRule(dashboardId, rule.id);
      } else {
        await activateDashboardAlertRule(dashboardId, rule.id);
      }
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  // ---------- Bước 2: Chọn kênh nhận (email / Slack / Webhook) ----------
  async function submitChannel(ruleId) {
    if (!channelForm.destination.trim()) return;
    setError(null);
    try {
      await addDashboardAlertChannel(dashboardId, ruleId, channelForm);
      setChannelForm({ channelType: "EMAIL", destination: "" });
      setAddingChannelToRule(null);
      await loadRuleDetail(ruleId);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function toggleChannelActive(ruleId, channel) {
    setError(null);
    try {
      if (channel.is_active) {
        await deactivateDashboardAlertChannel(dashboardId, ruleId, channel.id);
      } else {
        await activateDashboardAlertChannel(dashboardId, ruleId, channel.id);
      }
      await loadRuleDetail(ruleId);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function removeChannel(ruleId, channelId) {
    setError(null);
    try {
      await deleteDashboardAlertChannel(dashboardId, ruleId, channelId);
      await loadRuleDetail(ruleId);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  // ---------- Bước 3: Khi vượt ngưỡng -> gửi cảnh báo ----------
  const [evaluating, setEvaluating] = useState(null);
  const [evalResult, setEvalResult] = useState({}); // ruleId -> kết quả gần nhất

  async function evaluateNow(ruleId) {
    setEvaluating(ruleId);
    setError(null);
    try {
      const result = await evaluateDashboardAlertRule(dashboardId, ruleId);
      setEvalResult((prev) => ({ ...prev, [ruleId]: result }));
      await loadRuleDetail(ruleId);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setEvaluating(null);
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-header">
        <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          <BellRing size={16} /> UC-052 — Đăng ký nhận cảnh báo dashboard
        </h3>
        <p style={{ color: "#666", fontSize: 13, margin: "4px 0 0" }}>
          Cấu hình ngưỡng cảnh báo trên KPI, chọn kênh nhận (email/Slack/Webhook); khi vượt
          ngưỡng hệ thống gửi cảnh báo qua kênh đã chọn.
        </p>
      </div>
      <div className="card-body">
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 12 }}>
            {error}
          </div>
        )}
        {!userId && (
          <div className="alert alert-error">
            Không xác định được người dùng hiện tại — không thể cấu hình ngưỡng cảnh báo.
          </div>
        )}

        {/* Bước 1: form cấu hình ngưỡng */}
        <form onSubmit={submitRule} style={{ marginBottom: 16 }}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="alert-kpi-code">KPI</label>
              <select
                id="alert-kpi-code"
                value={form.kpiCode}
                onChange={(e) => setForm((f) => ({ ...f, kpiCode: e.target.value }))}
                disabled={kpis.length === 0}
              >
                {kpis.length === 0 && <option value="">(chưa có KPI)</option>}
                {kpis.map((k) => (
                  <option key={k.code} value={k.code}>
                    {k.name} ({k.code})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="alert-operator">Toán tử</label>
              <select
                id="alert-operator"
                value={form.operator}
                onChange={(e) => setForm((f) => ({ ...f, operator: e.target.value }))}
              >
                {Object.entries(OPERATOR_LABELS).map(([op, label]) => (
                  <option key={op} value={op}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="alert-threshold">Ngưỡng</label>
              <input
                id="alert-threshold"
                type="number"
                step="any"
                value={form.thresholdValue}
                onChange={(e) => setForm((f) => ({ ...f, thresholdValue: e.target.value }))}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="alert-year">Năm</label>
              <input
                id="alert-year"
                type="number"
                value={form.year}
                onChange={(e) => setForm((f) => ({ ...f, year: e.target.value }))}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="alert-org-unit">Đơn vị (tuỳ chọn)</label>
              <input
                id="alert-org-unit"
                value={form.orgUnitCode}
                onChange={(e) => setForm((f) => ({ ...f, orgUnitCode: e.target.value }))}
              />
            </div>
            <div className="field">
              <label htmlFor="alert-sector">Lĩnh vực (tuỳ chọn)</label>
              <input
                id="alert-sector"
                value={form.sector}
                onChange={(e) => setForm((f) => ({ ...f, sector: e.target.value }))}
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ marginTop: 14 }}
            disabled={saving || !userId || kpis.length === 0}
          >
            Lưu ngưỡng cảnh báo
          </button>
        </form>

        {loading && <p style={{ color: "#666" }}>Đang tải...</p>}

        {!loading && rules.length === 0 && (
          <p style={{ color: "#666" }}>Chưa có ngưỡng cảnh báo nào được cấu hình.</p>
        )}

        {!loading &&
          rules.map((rule) => {
            const detail = ruleDetails[rule.id] || { channels: [], logs: [] };
            const result = evalResult[rule.id];
            return (
              <div
                key={rule.id}
                className="card"
                style={{ marginBottom: 10, border: "1px solid #e2e2e2" }}
              >
                <div
                  className="card-body"
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}
                >
                  <div>
                    <strong>{rule.kpi_code}</strong>{" "}
                    <span className="badge">{rule.is_active ? "Đang bật" : "Đã tắt"}</span>
                    <div style={{ fontSize: 13, color: "#666" }}>
                      {OPERATOR_LABELS[rule.operator]} {rule.threshold_value} — năm {rule.year}
                      {rule.org_unit_code ? `, đơn vị ${rule.org_unit_code}` : ""}
                      {rule.sector ? `, lĩnh vực ${rule.sector}` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => toggleExpand(rule.id)}
                    >
                      {expandedRuleId === rule.id ? "Thu gọn" : "Kênh nhận & lịch sử"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => toggleRuleActive(rule)}
                    >
                      {rule.is_active ? "Tắt" : "Bật"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => evaluateNow(rule.id)}
                      disabled={evaluating === rule.id || !rule.is_active}
                      title="Đánh giá ngay: nếu vượt ngưỡng, hệ thống gửi cảnh báo qua kênh đã chọn"
                    >
                      <Send size={14} /> Đánh giá ngay
                    </button>
                  </div>
                </div>

                {result && (
                  <div
                    className="card-body"
                    style={{ borderTop: "1px solid #eee", fontSize: 13 }}
                  >
                    {result.triggered ? (
                      <span style={{ color: "#b91c1c" }}>
                        ⚠ Vượt ngưỡng — giá trị KPI hiện tại: {result.kpi_value}. Đã gửi cảnh báo
                        tới {result.logs.length} kênh.
                      </span>
                    ) : (
                      <span style={{ color: "#15803d" }}>
                        ✓ {result.reason} (giá trị KPI hiện tại: {result.kpi_value ?? "—"}).
                      </span>
                    )}
                  </div>
                )}

                {expandedRuleId === rule.id && (
                  <div className="card-body" style={{ borderTop: "1px solid #eee" }}>
                    <h4 style={{ margin: "0 0 8px" }}>Kênh nhận (email / Slack / Webhook)</h4>
                    <table className="data-table" style={{ marginBottom: 8 }}>
                      <thead>
                        <tr>
                          <th>Loại kênh</th>
                          <th>Địa chỉ nhận</th>
                          <th>Trạng thái</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.channels.length === 0 && (
                          <tr>
                            <td colSpan={4} style={{ color: "#666" }}>
                              Chưa có kênh nhận nào.
                            </td>
                          </tr>
                        )}
                        {detail.channels.map((c) => (
                          <tr key={c.id}>
                            <td>{CHANNEL_LABELS[c.channel_type]}</td>
                            <td>{c.destination}</td>
                            <td>{c.is_active ? "Đang bật" : "Đã tắt"}</td>
                            <td style={{ display: "flex", gap: 4 }}>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => toggleChannelActive(rule.id, c)}
                              >
                                {c.is_active ? "Tắt" : "Bật"}
                              </button>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => removeChannel(rule.id, c.id)}
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {addingChannelToRule === rule.id ? (
                      <div style={{ marginBottom: 12 }}>
                        <div className="form-grid">
                          <div className="field">
                            <label htmlFor={`channel-type-${rule.id}`}>Loại kênh</label>
                            <select
                              id={`channel-type-${rule.id}`}
                              value={channelForm.channelType}
                              onChange={(e) =>
                                setChannelForm((f) => ({ ...f, channelType: e.target.value }))
                              }
                            >
                              <option value="EMAIL">Email</option>
                              <option value="SLACK">Slack</option>
                              <option value="WEBHOOK">Webhook</option>
                            </select>
                          </div>
                          <div className="field">
                            <label htmlFor={`channel-destination-${rule.id}`}>
                              {channelForm.channelType === "EMAIL"
                                ? "Địa chỉ email"
                                : "URL webhook"}
                            </label>
                            <input
                              id={`channel-destination-${rule.id}`}
                              value={channelForm.destination}
                              onChange={(e) =>
                                setChannelForm((f) => ({ ...f, destination: e.target.value }))
                              }
                              placeholder={
                                channelForm.channelType === "EMAIL"
                                  ? "ten@stc.gov.vn"
                                  : "https://..."
                              }
                            />
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={() => submitChannel(rule.id)}
                          >
                            Lưu kênh
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setAddingChannelToRule(null)}
                          >
                            Huỷ
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ marginBottom: 12 }}
                        onClick={() => setAddingChannelToRule(rule.id)}
                      >
                        + Thêm kênh nhận
                      </button>
                    )}

                    <h4 style={{ margin: "0 0 8px" }}>Lịch sử gửi cảnh báo</h4>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Thời điểm</th>
                          <th>Kênh</th>
                          <th>Giá trị KPI</th>
                          <th>Trạng thái</th>
                          <th>Ghi chú</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.logs.length === 0 && (
                          <tr>
                            <td colSpan={5} style={{ color: "#666" }}>
                              Chưa có lượt gửi cảnh báo nào.
                            </td>
                          </tr>
                        )}
                        {detail.logs.map((log) => (
                          <tr key={log.id}>
                            <td>{log.triggered_at ? new Date(log.triggered_at).toLocaleString("vi-VN") : "—"}</td>
                            <td>{CHANNEL_LABELS[log.channel_type]}</td>
                            <td>{log.kpi_value ?? "—"}</td>
                            <td>{log.status === "SENT" ? "Đã gửi" : "Thất bại"}</td>
                            <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }}>
                              {log.message}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}