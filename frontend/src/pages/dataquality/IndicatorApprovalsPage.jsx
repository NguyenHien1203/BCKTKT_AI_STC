import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FlaskConical,
  Gavel,
  MinusCircle,
  PlusCircle,
  RefreshCw,
  ScrollText,
  Send,
  ShieldCheck,
  ShieldX,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listSemanticIndicators } from "../../api/semanticIndicators.js";
import {
  approveIndicator,
  getIndicatorComparison,
  listIndicatorApprovalDecisions,
  listPendingIndicatorApprovals,
  rejectIndicator,
  submitIndicatorForApproval,
} from "../../api/indicatorApprovals.js";

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("vi-VN", { maximumFractionDigits: 3 });
}

export default function IndicatorApprovalsPage() {
  const [domainFilter, setDomainFilter] = useState("");
  const [pending, setPending] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [decisions, setDecisions] = useState([]);

  const [draftIndicators, setDraftIndicators] = useState([]);
  const [submitTargetId, setSubmitTargetId] = useState("");
  const [submittedBy, setSubmittedBy] = useState("");

  const [decision, setDecision] = useState({ decided_by: "", reason: "" });

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittingApproval, setSubmittingApproval] = useState(false);

  // ---------- Tiền đề: danh sách chỉ tiêu DRAFT để gửi chờ duyệt ----------
  async function loadDraftIndicators() {
    try {
      const data = await listSemanticIndicators({ status: "DRAFT" });
      setDraftIndicators(data);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  // ---------- Bước 1: Xem chỉ tiêu chờ phê duyệt ----------
  async function loadPending(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listPendingIndicatorApprovals({ domain: domainFilter || null });
      setPending(data);
      if (!keepSelection || !data.some((i) => i.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  // ---------- Bước 2: Xem kết quả kiểm thử + so sánh với số liệu hiện tại ----------
  async function loadComparison(indicatorId) {
    if (!indicatorId) {
      setComparison(null);
      setDecisions([]);
      return;
    }
    setLoadingComparison(true);
    try {
      const [cmp, logs] = await Promise.all([
        getIndicatorComparison(indicatorId),
        listIndicatorApprovalDecisions(indicatorId),
      ]);
      setComparison(cmp);
      setDecisions(logs);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingComparison(false);
    }
  }

  useEffect(() => {
    loadPending(false);
    loadDraftIndicators();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainFilter]);

  useEffect(() => {
    loadComparison(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // ---------- Tiền đề: gửi chỉ tiêu chờ phê duyệt ----------
  async function handleSubmitForApproval(e) {
    e.preventDefault();
    if (!submitTargetId) {
      setError("Vui lòng chọn 1 chỉ tiêu đang Nháp để gửi chờ duyệt.");
      return;
    }
    setSubmitting(true);
    try {
      await submitIndicatorForApproval(submitTargetId, {
        submittedBy: submittedBy.trim() || null,
      });
      setInfo("Đã gửi chỉ tiêu chờ phê duyệt.");
      setError(null);
      setSubmitTargetId("");
      await Promise.all([loadPending(true), loadDraftIndicators()]);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 3: Phê duyệt / từ chối chỉ tiêu ----------
  async function handleDecision(action) {
    if (!selectedId) return;
    if (!decision.reason.trim()) {
      setError("Vui lòng ghi lý do phê duyệt/từ chối (bắt buộc, sẽ lưu vào nhật ký).");
      return;
    }
    setSubmittingApproval(true);
    try {
      const fn = action === "approve" ? approveIndicator : rejectIndicator;
      await fn(selectedId, {
        decidedBy: decision.decided_by.trim() || null,
        reason: decision.reason.trim(),
      });
      setInfo(
        action === "approve"
          ? "Đã duyệt -- chỉ tiêu đã được công bố (ACTIVE)."
          : "Đã từ chối -- chỉ tiêu đã được trả về cho Quản trị Dữ liệu (DRAFT).",
      );
      setError(null);
      setDecision({ decided_by: decision.decided_by, reason: "" });
      await Promise.all([loadPending(false), loadDraftIndicators()]);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmittingApproval(false);
    }
  }

  const selectedIndicator = pending.find((i) => i.id === selectedId) || null;
  const delta = comparison?.delta;
  const DeltaIcon = delta === null || delta === undefined ? null : delta >= 0 ? TrendingUp : TrendingDown;
  const deltaColor =
    delta === null || delta === undefined
      ? undefined
      : delta > 0
      ? "var(--color-success, #27ae60)"
      : delta < 0
      ? "var(--color-danger, #c0392b)"
      : undefined;

  return (
    <AppLayout
      title="Phê duyệt chỉ tiêu"
      subtitle="UC-044 — Xem chỉ tiêu chờ phê duyệt; xem kết quả kiểm thử + so sánh với số liệu hiện tại; phê duyệt/từ chối, hệ thống công bố hoặc trả về cho Quản trị Dữ liệu."
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

      {/* ---------- Tiền đề: gửi chỉ tiêu chờ phê duyệt ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>
            <Send size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Gửi chỉ tiêu chờ phê duyệt
          </h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmitForApproval} className="form-grid">
            <div className="field">
              <label htmlFor="submit-target">Chỉ tiêu đang Nháp (UC-043)</label>
              <select
                id="submit-target"
                value={submitTargetId}
                onChange={(e) => setSubmitTargetId(e.target.value)}
              >
                <option value="">-- Chọn chỉ tiêu --</option>
                {draftIndicators.map((i) => (
                  <option key={i.id} value={i.id}>
                    #{i.id} — {i.name} ({i.domain})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="submitted-by">Người gửi</label>
              <input
                id="submitted-by"
                value={submittedBy}
                onChange={(e) => setSubmittedBy(e.target.value)}
                placeholder="Quản trị Dữ liệu"
              />
            </div>
            <div className="field field-full">
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                <Send size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                {submitting ? "Đang gửi..." : "Gửi chờ duyệt"}
              </button>
            </div>
          </form>
          {draftIndicators.length === 0 && (
            <div className="empty-state" style={{ marginTop: 8 }}>
              Không có chỉ tiêu nào đang ở trạng thái Nháp.
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 1: Chỉ tiêu chờ phê duyệt ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 1 — Chỉ tiêu chờ phê duyệt</h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadPending(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="domain-filter">Lĩnh vực</label>
                <input
                  id="domain-filter"
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value)}
                  placeholder="Vd Ngân sách"
                />
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : pending.length === 0 ? (
              <div className="empty-state">Không có chỉ tiêu nào đang chờ duyệt.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {pending.map((i) => (
                  <div
                    key={i.id}
                    onClick={() => setSelectedId(i.id)}
                    style={{
                      cursor: "pointer",
                      border: "1px solid var(--color-border, #eee)",
                      borderRadius: 6,
                      padding: 10,
                      background: selectedId === i.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>
                        <FlaskConical size={13} style={{ verticalAlign: "middle", marginRight: 4 }} />
                        <strong>{i.name}</strong>
                      </span>
                      <span className="badge badge-warning">Chờ duyệt</span>
                    </div>
                    <div style={{ fontSize: 13, marginTop: 4 }}>
                      Lĩnh vực: {i.domain} — v{i.version}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      {i.expression}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ---------- Bước 2 & 3: So sánh + Phê duyệt/Từ chối ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              Bước 2 — Kết quả kiểm thử + so sánh{" "}
              {selectedIndicator ? `(chỉ tiêu #${selectedIndicator.id})` : ""}
            </h2>
          </div>
          <div className="card-body">
            {!selectedId ? (
              <div className="empty-state">Chọn 1 chỉ tiêu ở bên trái để xem chi tiết.</div>
            ) : loadingComparison ? (
              <p>Đang tải...</p>
            ) : comparison ? (
              <>
                <div style={{ marginBottom: 12, fontSize: 13 }}>
                  Biểu thức: <code>{comparison.indicator.expression}</code>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
                  <div style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 12 }}>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Số liệu hiện tại (đang ACTIVE)</div>
                    <div style={{ fontSize: 20, fontWeight: 600 }}>{formatNumber(comparison.current_value)}</div>
                    {!comparison.has_current_value && (
                      <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
                        Chưa từng được công bố trước đó
                      </div>
                    )}
                  </div>
                  <div style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 12 }}>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Kết quả kiểm thử mới nhất</div>
                    <div style={{ fontSize: 20, fontWeight: 600 }}>{formatNumber(comparison.new_value)}</div>
                    {comparison.latest_test_run && (
                      <div
                        className={`badge ${comparison.latest_test_run.status === "SUCCESS" ? "badge-success" : "badge-danger"}`}
                        style={{ marginTop: 4 }}
                      >
                        {comparison.latest_test_run.status}
                      </div>
                    )}
                  </div>
                  <div style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 12 }}>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Chênh lệch</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: deltaColor, display: "flex", alignItems: "center", gap: 4 }}>
                      {DeltaIcon && <DeltaIcon size={18} />}
                      {formatNumber(delta)}
                      {comparison.delta_percent !== null && comparison.delta_percent !== undefined && (
                        <span style={{ fontSize: 13, fontWeight: 400 }}>
                          ({comparison.delta_percent >= 0 ? "+" : ""}
                          {comparison.delta_percent.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {comparison.latest_test_run?.status === "FAILED" && (
                  <div className="alert alert-error" style={{ marginBottom: 16 }}>
                    <AlertCircle size={16} />
                    <span>Lượt kiểm thử mới nhất lỗi: {comparison.latest_test_run.error_message}</span>
                  </div>
                )}

                {/* ---------- Bước 3: Phê duyệt / Từ chối ---------- */}
                <div style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 12 }}>
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>
                    <Gavel size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    Bước 3 — Phê duyệt / từ chối (lý do bắt buộc, lưu vào nhật ký)
                  </h3>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="decided-by">Người phê duyệt</label>
                      <input
                        id="decided-by"
                        value={decision.decided_by}
                        onChange={(e) => setDecision((d) => ({ ...d, decided_by: e.target.value }))}
                        placeholder="Chủ quản Nghiệp vụ"
                      />
                    </div>
                    <div className="field field-full">
                      <label htmlFor="decision-reason">Lý do phê duyệt / từ chối *</label>
                      <input
                        id="decision-reason"
                        value={decision.reason}
                        onChange={(e) => setDecision((d) => ({ ...d, reason: e.target.value }))}
                        placeholder="Bắt buộc -- sẽ được lưu vào nhật ký"
                      />
                    </div>
                    <div className="field field-full" style={{ display: "flex", gap: 8 }}>
                      <button
                        className="btn btn-primary"
                        disabled={submittingApproval}
                        onClick={() => handleDecision("approve")}
                      >
                        <ShieldCheck size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                        {submittingApproval ? "Đang xử lý..." : "Duyệt — công bố"}
                      </button>
                      <button
                        className="btn btn-secondary"
                        disabled={submittingApproval}
                        onClick={() => handleDecision("reject")}
                      >
                        <ShieldX size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                        {submittingApproval ? "Đang xử lý..." : "Từ chối — trả về"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* ---------- Nhật ký quyết định ---------- */}
                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <ScrollText size={16} /> Nhật ký phê duyệt của chỉ tiêu này
                </h3>
                {decisions.length === 0 ? (
                  <div className="empty-state">Chưa có quyết định nào được ghi.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {decisions.map((d) => (
                      <div key={d.id} style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 10 }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>
                            <strong>{d.decided_by || "—"}</strong>{" "}
                            <Clock size={12} style={{ verticalAlign: "middle" }} /> {formatTime(d.created_at)}
                          </span>
                          <span className={`badge ${d.action === "APPROVED" ? "badge-success" : "badge-danger"}`}>
                            {d.action === "APPROVED" ? (
                              <>
                                <PlusCircle size={12} style={{ verticalAlign: "middle", marginRight: 2 }} />
                                Đã duyệt
                              </>
                            ) : (
                              <>
                                <MinusCircle size={12} style={{ verticalAlign: "middle", marginRight: 2 }} />
                                Đã từ chối
                              </>
                            )}
                          </span>
                        </div>
                        <div style={{ fontSize: 13, marginTop: 4 }}>Lý do: {d.decision_reason}</div>
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 2 }}>
                          Số liệu hiện tại lúc quyết định: {formatNumber(d.comparison_snapshot?.current_value)} → Kết quả kiểm thử:{" "}
                          {formatNumber(d.comparison_snapshot?.new_value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : null}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}