import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Lock,
  PlusCircle,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listTabmisIntakeSessions } from "../../api/tabmisIntake.js";
import {
  closeIntakeReconciliation,
  getIntakeReconciliation,
  markIntakeReconciliationFinding,
  openIntakeReconciliation,
  resolveIntakeReconciliationFinding,
} from "../../api/intakeReconciliation.js";

const FINDING_TYPE_LABEL = {
  MISSING: "Thiếu dữ liệu",
  INCORRECT: "Sai lệch dữ liệu",
};

const FINDING_STATUS_BADGE = {
  OPEN: "badge-warning",
  RESOLVED: "badge-success",
};

const FINDING_STATUS_LABEL = {
  OPEN: "Chưa xử lý",
  RESOLVED: "Đã xử lý",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function IntakeReconciliationPage() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState("");
  const [reconciledBy, setReconciledBy] = useState("qtth01");

  const [reconciliation, setReconciliation] = useState(null);

  const [findingType, setFindingType] = useState("MISSING");
  const [fieldName, setFieldName] = useState("");
  const [description, setDescription] = useState("");

  const [closedBy, setClosedBy] = useState("qtth01");
  const [closeNote, setCloseNote] = useState("");

  const [loadingSessions, setLoadingSessions] = useState(false);
  const [opening, setOpening] = useState(false);
  const [marking, setMarking] = useState(false);
  const [closing, setClosing] = useState(false);
  const [resolvingIndex, setResolvingIndex] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function loadSessions() {
    setLoadingSessions(true);
    try {
      const data = await listTabmisIntakeSessions({});
      setSessions(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingSessions(false);
    }
  }

  useEffect(() => {
    loadSessions();
  }, []);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 4000);
  }

  async function refreshReconciliation(reconciliationId) {
    const data = await getIntakeReconciliation(reconciliationId);
    setReconciliation(data);
    return data;
  }

  // ---------- Bước 1-2: Chọn phiên cần đối soát -> hệ thống hiển thị tổng kiểm soát ----------

  async function handleOpen(e) {
    e.preventDefault();
    if (!sessionId) {
      setError("Vui lòng chọn phiên tiếp nhận cần đối soát");
      return;
    }
    setOpening(true);
    try {
      const data = await openIntakeReconciliation({
        sessionId: Number(sessionId),
        reconciledBy,
      });
      setReconciliation(data);
      setError(null);
      flashSuccess(
        `Đã mở phiên đối soát #${data.id} cho phiên tiếp nhận #${data.session_id} — hệ thống hiển thị tổng kiểm soát bên dưới.`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setOpening(false);
    }
  }

  // ---------- Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu ----------

  async function handleMarkFinding(e) {
    e.preventDefault();
    if (!reconciliation) return;
    if (!fieldName.trim() || !description.trim()) {
      setError("Vui lòng nhập trường/mục phát hiện và nội dung phát hiện");
      return;
    }
    setMarking(true);
    try {
      await markIntakeReconciliationFinding(reconciliation.id, {
        findingType,
        fieldName,
        description,
      });
      setFieldName("");
      setDescription("");
      await refreshReconciliation(reconciliation.id);
      setError(null);
      flashSuccess("Đã đánh dấu phát hiện thiếu/sai — hệ thống đã lưu.");
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setMarking(false);
    }
  }

  async function handleResolveFinding(index) {
    if (!reconciliation) return;
    setResolvingIndex(index);
    try {
      await resolveIntakeReconciliationFinding(reconciliation.id, index);
      await refreshReconciliation(reconciliation.id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setResolvingIndex(null);
    }
  }

  // ---------- Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> hệ thống cập nhật trạng thái ----------

  async function handleClose(e) {
    e.preventDefault();
    if (!reconciliation) return;
    setClosing(true);
    try {
      const data = await closeIntakeReconciliation(reconciliation.id, {
        closedBy,
        closeNote,
      });
      setReconciliation(data);
      setError(null);
      flashSuccess(
        `Đã đóng phiên đối soát #${data.id} — đạt yêu cầu, hệ thống đã cập nhật trạng thái CLOSED.`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setClosing(false);
    }
  }

  const openFindingCount = reconciliation
    ? reconciliation.findings.filter((f) => f.status === "OPEN").length
    : 0;
  const isClosed = reconciliation?.status === "CLOSED";

  return (
    <AppLayout
      title="Đối soát phiên intake"
      subtitle="UC-027 — Chọn phiên tiếp nhận cần đối soát, hệ thống hiển thị tổng kiểm soát; đánh dấu các phát hiện thiếu/sai, hệ thống lưu; đóng phiên đối soát đạt yêu cầu để hệ thống cập nhật trạng thái."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{success}</span>
        </div>
      )}

      {/* Bước 1: Chọn phiên cần đối soát */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bước 1 — Chọn phiên cần đối soát</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleOpen}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="session_id">Phiên tiếp nhận TABMIS</label>
                <select
                  id="session_id"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  required
                >
                  <option value="" disabled>
                    -- Chọn phiên tiếp nhận --
                  </option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      #{s.id} — {s.file_name} ({s.status})
                    </option>
                  ))}
                </select>
                {!loadingSessions && sessions.length === 0 && (
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Chưa có phiên tiếp nhận TABMIS nào (xem trang "Tiếp nhận file thủ công
                    TABMIS").
                  </div>
                )}
              </div>
              <div className="field">
                <label htmlFor="reconciled_by">Người thực hiện đối soát</label>
                <input
                  id="reconciled_by"
                  value={reconciledBy}
                  onChange={(e) => setReconciledBy(e.target.value)}
                  required
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button type="submit" className="btn btn-primary" disabled={opening}>
                  <ClipboardCheck size={15} />
                  {opening ? "Đang mở..." : "Chọn phiên & mở đối soát"}
                </button>
              </div>
            </div>
          </form>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 8 }}>
            Nếu phiên tiếp nhận đã có 1 lượt đối soát đang mở, hệ thống sẽ dùng lại lượt đó
            (không tạo trùng).
          </div>
        </div>
      </div>

      {reconciliation && (
        <>
          {/* Bước 2: Hệ thống hiển thị tổng kiểm soát */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
              <h2>Bước 2 — Tổng kiểm soát của phiên đối soát #{reconciliation.id}</h2>
              <span
                className={`badge ${isClosed ? "badge-success" : "badge-warning"}`}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                {isClosed && <Lock size={12} />}
                {isClosed ? "Đã đóng" : "Đang mở"}
              </span>
            </div>
            <div className="card-body">
              <table className="data-table">
                <tbody>
                  <tr>
                    <td style={{ width: 220 }}>Phiên tiếp nhận</td>
                    <td>#{reconciliation.session_id}</td>
                  </tr>
                  <tr>
                    <td>Số dòng dữ liệu đọc được</td>
                    <td>{reconciliation.control_totals?.records_read ?? 0}</td>
                  </tr>
                  <tr>
                    <td>Số cột khớp / kỳ vọng</td>
                    <td>
                      {reconciliation.control_totals?.columns_found ?? 0} /{" "}
                      {reconciliation.control_totals?.columns_expected ?? 0}
                    </td>
                  </tr>
                  <tr>
                    <td>Số dòng dữ liệu sai (tại thời điểm tiếp nhận)</td>
                    <td>{reconciliation.control_totals?.row_error_count ?? 0}</td>
                  </tr>
                  <tr>
                    <td>Người thực hiện đối soát</td>
                    <td>{reconciliation.reconciled_by}</td>
                  </tr>
                  <tr>
                    <td>Thời điểm mở đối soát</td>
                    <td>{formatTime(reconciliation.opened_at)}</td>
                  </tr>
                  {isClosed && (
                    <>
                      <tr>
                        <td>Người đóng phiên đối soát</td>
                        <td>{reconciliation.closed_by}</td>
                      </tr>
                      <tr>
                        <td>Thời điểm đóng</td>
                        <td>{formatTime(reconciliation.closed_at)}</td>
                      </tr>
                      <tr>
                        <td>Ghi chú khi đóng</td>
                        <td>{reconciliation.close_note || "—"}</td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>
                Bước 3-4 — Đánh dấu phát hiện thiếu/sai ({reconciliation.findings.length})
              </h2>
            </div>
            <div className="card-body">
              {!isClosed && (
                <form onSubmit={handleMarkFinding} style={{ marginBottom: 16 }}>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="finding_type">Loại phát hiện</label>
                      <select
                        id="finding_type"
                        value={findingType}
                        onChange={(e) => setFindingType(e.target.value)}
                      >
                        <option value="MISSING">Thiếu dữ liệu</option>
                        <option value="INCORRECT">Sai lệch dữ liệu</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="field_name">Trường / mục phát hiện</label>
                      <input
                        id="field_name"
                        value={fieldName}
                        onChange={(e) => setFieldName(e.target.value)}
                        placeholder="vd: so_tien, DV03..."
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="description">Nội dung phát hiện</label>
                      <input
                        id="description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Mô tả chi tiết thiếu/sai so với tổng kiểm soát"
                        required
                      />
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-end" }}>
                      <button type="submit" className="btn btn-primary" disabled={marking}>
                        <PlusCircle size={15} />
                        {marking ? "Đang lưu..." : "Đánh dấu phát hiện"}
                      </button>
                    </div>
                  </div>
                </form>
              )}

              {reconciliation.findings.length === 0 ? (
                <div className="empty-state">
                  Chưa có phát hiện thiếu/sai nào được đánh dấu cho phiên đối soát này.
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Loại</th>
                      <th>Trường/mục</th>
                      <th>Nội dung</th>
                      <th>Trạng thái</th>
                      <th>Ghi nhận lúc</th>
                      {!isClosed && <th></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {reconciliation.findings.map((f, idx) => (
                      <tr key={idx}>
                        <td>{idx}</td>
                        <td>{FINDING_TYPE_LABEL[f.finding_type] || f.finding_type}</td>
                        <td>{f.field_name}</td>
                        <td>{f.description}</td>
                        <td>
                          <span
                            className={`badge ${FINDING_STATUS_BADGE[f.status] || "badge-neutral"}`}
                          >
                            {FINDING_STATUS_LABEL[f.status] || f.status}
                          </span>
                        </td>
                        <td>{formatTime(f.recorded_at)}</td>
                        {!isClosed && (
                          <td>
                            {f.status === "OPEN" && (
                              <button
                                type="button"
                                className="btn"
                                style={{ padding: "4px 10px", fontSize: 12 }}
                                onClick={() => handleResolveFinding(idx)}
                                disabled={resolvingIndex === idx}
                              >
                                {resolvingIndex === idx ? "Đang xử lý..." : "Đánh dấu đã xử lý"}
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> hệ thống cập nhật trạng thái */}
          <div className="card">
            <div className="card-header">
              <h2>Bước 5-6 — Đóng phiên đối soát đạt yêu cầu</h2>
            </div>
            <div className="card-body">
              {isClosed ? (
                <div className="alert alert-success">
                  <CheckCircle2 size={16} />
                  <span>Phiên đối soát đã đóng — hệ thống đã cập nhật trạng thái CLOSED.</span>
                </div>
              ) : (
                <>
                  {openFindingCount > 0 && (
                    <div className="alert alert-error" style={{ marginBottom: 12 }}>
                      <AlertCircle size={16} />
                      <span>
                        Chưa đạt yêu cầu để đóng: còn {openFindingCount} phát hiện thiếu/sai
                        chưa được xử lý xong.
                      </span>
                    </div>
                  )}
                  <form onSubmit={handleClose}>
                    <div className="form-grid">
                      <div className="field">
                        <label htmlFor="closed_by">Người đóng phiên đối soát</label>
                        <input
                          id="closed_by"
                          value={closedBy}
                          onChange={(e) => setClosedBy(e.target.value)}
                          required
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="close_note">Ghi chú (không bắt buộc)</label>
                        <input
                          id="close_note"
                          value={closeNote}
                          onChange={(e) => setCloseNote(e.target.value)}
                          placeholder="vd: Đã bổ sung/đối chiếu xong, đạt yêu cầu"
                        />
                      </div>
                      <div style={{ display: "flex", alignItems: "flex-end" }}>
                        <button
                          type="submit"
                          className="btn btn-primary"
                          disabled={closing || openFindingCount > 0}
                        >
                          <Lock size={15} />
                          {closing ? "Đang đóng..." : "Đóng phiên đối soát"}
                        </button>
                      </div>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}