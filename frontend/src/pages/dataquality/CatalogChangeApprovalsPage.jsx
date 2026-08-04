import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  Landmark,
  Package,
  RefreshCw,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  approveChangeRequest,
  getChangeRequestDiff,
  listChangeApprovalAuditLogs,
  listPendingChangeRequests,
  rejectChangeRequest,
} from "../../api/catalogChangeApprovals.js";

const CATALOG_LABELS = {
  ITEM: { label: "Mặt hàng", icon: Package },
  DOCUMENT_TYPE: { label: "Loại văn bản", icon: FileText },
  FUNDING_SOURCE: { label: "Nguồn vốn", icon: Landmark },
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function formatValue(v) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Có" : "Không";
  return String(v);
}

export default function CatalogChangeApprovalsPage() {
  const [catalogType, setCatalogType] = useState("");
  const [pending, setPending] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [diff, setDiff] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);

  const [decision, setDecision] = useState({ decided_by: "", reason: "" });

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // ---------- Bước 1: Xem các yêu cầu chờ duyệt ----------
  async function loadPending(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listPendingChangeRequests({ catalogType: catalogType || null });
      setPending(data);
      if (!keepSelection || !data.some((r) => r.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  // ---------- Bước 2: Hệ thống hiển thị diff ----------
  async function loadDiff(requestId) {
    if (!requestId) {
      setDiff(null);
      setAuditLogs([]);
      return;
    }
    setLoadingDiff(true);
    try {
      const [d, logs] = await Promise.all([
        getChangeRequestDiff(requestId),
        listChangeApprovalAuditLogs({ requestId }),
      ]);
      setDiff(d);
      setAuditLogs(logs);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingDiff(false);
    }
  }

  useEffect(() => {
    loadPending(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogType]);

  useEffect(() => {
    loadDiff(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // ---------- Bước 3 + 4 + 5: Phê duyệt / Từ chối -- áp dụng -- ghi nhật ký ----------
  async function handleDecision(action) {
    if (!selectedId) return;
    if (!decision.decided_by.trim()) {
      setError("Vui lòng nhập người phê duyệt.");
      return;
    }
    if (!decision.reason.trim()) {
      setError("Vui lòng ghi lý do phê duyệt/từ chối trước khi lưu vào nhật ký (bắt buộc).");
      return;
    }
    setSubmitting(true);
    try {
      const fn = action === "approve" ? approveChangeRequest : rejectChangeRequest;
      await fn(selectedId, { decidedBy: decision.decided_by.trim(), reason: decision.reason.trim() });
      setInfo(
        action === "approve"
          ? "Đã duyệt -- thay đổi được áp dụng vào danh mục và ghi vào nhật ký."
          : "Đã từ chối -- lý do đã được ghi vào nhật ký.",
      );
      setError(null);
      setDecision({ decided_by: decision.decided_by, reason: "" });
      await loadPending(false);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const selectedRequest = pending.find((r) => r.id === selectedId) || null;

  return (
    <AppLayout
      title="Phê duyệt thay đổi danh mục nhạy cảm"
      subtitle="UC-037 — Xem các yêu cầu chờ duyệt; hệ thống hiển thị diff; phê duyệt/từ chối (áp dụng thay đổi + ghi lý do vào nhật ký)."
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 1: Danh sách yêu cầu chờ duyệt ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 1 — Yêu cầu chờ duyệt</h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadPending(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="catalog-type-filter">Danh mục</label>
                <select
                  id="catalog-type-filter"
                  value={catalogType}
                  onChange={(e) => setCatalogType(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  <option value="ITEM">Mặt hàng</option>
                  <option value="DOCUMENT_TYPE">Loại văn bản</option>
                  <option value="FUNDING_SOURCE">Nguồn vốn</option>
                </select>
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : pending.length === 0 ? (
              <div className="empty-state">Không có yêu cầu nào đang chờ duyệt.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {pending.map((r) => {
                  const meta = CATALOG_LABELS[r.catalog_type] || {};
                  const Icon = meta.icon || ShieldAlert;
                  return (
                    <div
                      key={r.id}
                      onClick={() => setSelectedId(r.id)}
                      style={{
                        cursor: "pointer",
                        border: "1px solid var(--color-border, #eee)",
                        borderRadius: 6,
                        padding: 10,
                        background:
                          selectedId === r.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>
                          <Icon size={13} style={{ verticalAlign: "middle", marginRight: 4 }} />
                          <strong>{meta.label || r.catalog_type}</strong>
                        </span>
                        <span className="badge badge-warning">PENDING</span>
                      </div>
                      <div style={{ fontSize: 13, marginTop: 4 }}>
                        Đề nghị bởi <strong>{r.requested_by}</strong> lúc{" "}
                        {formatTime(r.created_at)}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                        Lý do: {r.reason}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ---------- Bước 2 & 3: Diff + Phê duyệt/Từ chối ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              Bước 2 — Diff{" "}
              {selectedRequest ? `(yêu cầu #${selectedRequest.id})` : ""}
            </h2>
          </div>
          <div className="card-body">
            {!selectedId ? (
              <div className="empty-state">Chọn 1 yêu cầu ở bên trái để xem chi tiết.</div>
            ) : loadingDiff ? (
              <p>Đang tải...</p>
            ) : diff ? (
              <>
                <div style={{ marginBottom: 12, fontSize: 13 }}>
                  Mục danh mục: <strong>{diff.entry.code}</strong> — {diff.entry.name} (phiên bản
                  hiện tại v{diff.entry.version})
                </div>

                {diff.changes.length === 0 ? (
                  <div className="empty-state">Yêu cầu này không đề nghị thay đổi trường nào.</div>
                ) : (
                  <table className="table" style={{ marginBottom: 16 }}>
                    <thead>
                      <tr>
                        <th>Trường</th>
                        <th>Giá trị hiện tại</th>
                        <th>Giá trị đề nghị</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diff.changes.map((c) => (
                        <tr key={c.field}>
                          <td>{c.field_label}</td>
                          <td style={{ color: "var(--color-danger, #c0392b)" }}>
                            {formatValue(c.old_value)}
                          </td>
                          <td style={{ color: "var(--color-success, #27ae60)" }}>
                            <strong>{formatValue(c.new_value)}</strong>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                <div style={{ fontSize: 13, marginBottom: 16 }}>
                  Lý do đề nghị: {diff.request.reason}
                </div>

                {/* ---------- Bước 3+4+5: Phê duyệt / Từ chối ---------- */}
                <div
                  style={{
                    border: "1px solid var(--color-border, #eee)",
                    borderRadius: 6,
                    padding: 12,
                  }}
                >
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>
                    Bước 3 — Phê duyệt / từ chối (bước 5: lý do bắt buộc, lưu vào nhật ký)
                  </h3>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="decided-by">Người phê duyệt *</label>
                      <input
                        id="decided-by"
                        value={decision.decided_by}
                        onChange={(e) =>
                          setDecision((d) => ({ ...d, decided_by: e.target.value }))
                        }
                        placeholder="Lãnh đạo Phòng nghiệp vụ"
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
                        disabled={submitting}
                        onClick={() => handleDecision("approve")}
                      >
                        <ShieldCheck size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                        {submitting ? "Đang xử lý..." : "Duyệt"}
                      </button>
                      <button
                        className="btn btn-secondary"
                        disabled={submitting}
                        onClick={() => handleDecision("reject")}
                      >
                        <ShieldX size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                        {submitting ? "Đang xử lý..." : "Từ chối"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* ---------- Bước 5: Nhật ký ---------- */}
                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <ScrollText size={16} /> Nhật ký phê duyệt của yêu cầu này
                </h3>
                {auditLogs.length === 0 ? (
                  <div className="empty-state">Chưa có quyết định nào được ghi.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {auditLogs.map((log) => (
                      <div
                        key={log.id}
                        style={{
                          border: "1px solid var(--color-border, #eee)",
                          borderRadius: 6,
                          padding: 10,
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>
                            <strong>{log.decided_by}</strong>{" "}
                            <Clock size={12} style={{ verticalAlign: "middle" }} />{" "}
                            {formatTime(log.created_at)}
                          </span>
                          <span
                            className={`badge ${
                              log.action === "APPROVED" ? "badge-success" : "badge-danger"
                            }`}
                          >
                            {log.action === "APPROVED" ? "Đã duyệt" : "Đã từ chối"}
                          </span>
                        </div>
                        <div style={{ fontSize: 13, marginTop: 4 }}>
                          Lý do: {log.decision_reason}
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