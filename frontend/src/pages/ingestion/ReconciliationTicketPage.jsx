import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Lock, PlusCircle, Ticket } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listIntakeReconciliations } from "../../api/intakeReconciliation.js";
import {
  addReconciliationTicketProgress,
  closeReconciliationTicket,
  getReconciliationTicket,
  listReconciliationTickets,
  openReconciliationTicket,
} from "../../api/reconciliationTicket.js";

const STATUS_LABEL = {
  OPEN: "Mở",
  IN_PROGRESS: "Đang xử lý",
  RESOLVED: "Đã xử lý (chờ đóng)",
  CLOSED: "Đã đóng",
};

const STATUS_BADGE = {
  OPEN: "badge-warning",
  IN_PROGRESS: "badge-warning",
  RESOLVED: "badge-success",
  CLOSED: "badge-neutral",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function ReconciliationTicketPage() {
  const [reconciliations, setReconciliations] = useState([]);
  const [reconciliationId, setReconciliationId] = useState("");
  const [sourceOwner, setSourceOwner] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [openedBy, setOpenedBy] = useState("qtth01");

  const [tickets, setTickets] = useState([]);
  const [ticket, setTicket] = useState(null);

  const [progressNote, setProgressNote] = useState("");
  const [progressUpdatedBy, setProgressUpdatedBy] = useState("qtth01");
  const [progressStatus, setProgressStatus] = useState("IN_PROGRESS");

  const [closedBy, setClosedBy] = useState("qtth01");
  const [closeNote, setCloseNote] = useState("");

  const [loadingReconciliations, setLoadingReconciliations] = useState(false);
  const [opening, setOpening] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [closing, setClosing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function loadReconciliations() {
    setLoadingReconciliations(true);
    try {
      const data = await listIntakeReconciliations({});
      setReconciliations(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingReconciliations(false);
    }
  }

  async function loadTicketsFor(recId) {
    if (!recId) {
      setTickets([]);
      return;
    }
    try {
      const data = await listReconciliationTickets({ reconciliationId: Number(recId) });
      setTickets(data);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadReconciliations();
  }, []);

  useEffect(() => {
    loadTicketsFor(reconciliationId);
    setTicket(null);
  }, [reconciliationId]);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 4000);
  }

  async function refreshTicket(ticketId) {
    const data = await getReconciliationTicket(ticketId);
    setTicket(data);
    await loadTicketsFor(reconciliationId);
    return data;
  }

  // ---------- Bước 1: Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu + thông báo ----------

  async function handleOpen(e) {
    e.preventDefault();
    if (!reconciliationId) {
      setError("Vui lòng chọn phiên đối soát cần mở ticket");
      return;
    }
    if (!sourceOwner.trim() || !title.trim()) {
      setError("Vui lòng nhập chủ quản nguồn và tiêu đề ticket");
      return;
    }
    setOpening(true);
    try {
      const data = await openReconciliationTicket({
        reconciliationId: Number(reconciliationId),
        sourceOwner,
        title,
        description,
        openedBy,
      });
      setTicket(data);
      await loadTicketsFor(reconciliationId);
      setTitle("");
      setDescription("");
      setError(null);
      flashSuccess(
        `Đã mở ticket #${data.id} với chủ quản nguồn "${data.source_owner}" — hệ thống đã lưu và thông báo.`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setOpening(false);
    }
  }

  // ---------- Bước 2: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử ----------

  async function handleAddProgress(e) {
    e.preventDefault();
    if (!ticket) return;
    if (!progressNote.trim() || !progressUpdatedBy.trim()) {
      setError("Vui lòng nhập nội dung cập nhật và người cập nhật");
      return;
    }
    setUpdating(true);
    try {
      await addReconciliationTicketProgress(ticket.id, {
        note: progressNote,
        updatedBy: progressUpdatedBy,
        status: progressStatus,
      });
      setProgressNote("");
      await refreshTicket(ticket.id);
      setError(null);
      flashSuccess("Đã cập nhật tiến độ xử lý ticket — hệ thống đã lưu vào lịch sử.");
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setUpdating(false);
    }
  }

  // ---------- Bước 3: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký ----------

  async function handleClose(e) {
    e.preventDefault();
    if (!ticket) return;
    setClosing(true);
    try {
      const data = await closeReconciliationTicket(ticket.id, { closedBy, closeNote });
      setTicket(data);
      await loadTicketsFor(reconciliationId);
      setError(null);
      flashSuccess(`Đã đóng ticket #${data.id} — hệ thống đã cập nhật trạng thái CLOSED + ghi nhật ký.`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setClosing(false);
    }
  }

  const isClosed = ticket?.status === "CLOSED";
  const isResolved = ticket?.status === "RESOLVED";

  return (
    <AppLayout
      title="Xử lý ticket đối soát với chủ quản nguồn"
      subtitle="UC-028 — Mở ticket xử lý với chủ quản nguồn của phiên đối soát, hệ thống lưu + thông báo; cập nhật tiến độ xử lý, hệ thống lưu lịch sử; đóng ticket khi đã resolved để hệ thống cập nhật trạng thái + ghi nhật ký."
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

      {/* Bước 1: Mở ticket xử lý với chủ quản nguồn */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bước 1 — Mở ticket xử lý với chủ quản nguồn</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleOpen}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="reconciliation_id">Phiên đối soát</label>
                <select
                  id="reconciliation_id"
                  value={reconciliationId}
                  onChange={(e) => setReconciliationId(e.target.value)}
                  required
                >
                  <option value="" disabled>
                    -- Chọn phiên đối soát --
                  </option>
                  {reconciliations.map((r) => (
                    <option key={r.id} value={r.id}>
                      #{r.id} — phiên tiếp nhận #{r.session_id} ({r.status}, {r.findings.length} phát
                      hiện)
                    </option>
                  ))}
                </select>
                {!loadingReconciliations && reconciliations.length === 0 && (
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Chưa có phiên đối soát nào (xem trang "Đối soát phiên intake").
                  </div>
                )}
              </div>
              <div className="field">
                <label htmlFor="source_owner">Chủ quản nguồn</label>
                <input
                  id="source_owner"
                  value={sourceOwner}
                  onChange={(e) => setSourceOwner(e.target.value)}
                  placeholder="vd: Cục CNTT - TABMIS"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="title">Tiêu đề ticket</label>
                <input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="vd: Đề nghị xác nhận thiếu bản ghi DV03"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="description">Mô tả (không bắt buộc)</label>
                <input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Mô tả chi tiết nội dung cần chủ quản nguồn xử lý"
                />
              </div>
              <div className="field">
                <label htmlFor="opened_by">Người mở ticket</label>
                <input
                  id="opened_by"
                  value={openedBy}
                  onChange={(e) => setOpenedBy(e.target.value)}
                  required
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button type="submit" className="btn btn-primary" disabled={opening}>
                  <Ticket size={15} />
                  {opening ? "Đang mở..." : "Mở ticket"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Danh sách ticket của phiên đối soát đang chọn */}
      {reconciliationId && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Ticket của phiên đối soát #{reconciliationId} ({tickets.length})</h2>
          </div>
          <div className="card-body">
            {tickets.length === 0 ? (
              <div className="empty-state">Chưa có ticket nào được mở cho phiên đối soát này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Chủ quản nguồn</th>
                    <th>Tiêu đề</th>
                    <th>Trạng thái</th>
                    <th>Mở lúc</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr key={t.id}>
                      <td>{t.id}</td>
                      <td>{t.source_owner}</td>
                      <td>{t.title}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[t.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[t.status] || t.status}
                        </span>
                      </td>
                      <td>{formatTime(t.opened_at)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn"
                          style={{ padding: "4px 10px", fontSize: 12 }}
                          onClick={() => refreshTicket(t.id)}
                        >
                          Xem chi tiết
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {ticket && (
        <>
          {/* Chi tiết ticket */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
              <h2>Ticket #{ticket.id}</h2>
              <span
                className={`badge ${STATUS_BADGE[ticket.status] || "badge-neutral"}`}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                {isClosed && <Lock size={12} />}
                {STATUS_LABEL[ticket.status] || ticket.status}
              </span>
            </div>
            <div className="card-body">
              <table className="data-table">
                <tbody>
                  <tr>
                    <td style={{ width: 220 }}>Phiên đối soát</td>
                    <td>#{ticket.reconciliation_id}</td>
                  </tr>
                  <tr>
                    <td>Chủ quản nguồn</td>
                    <td>{ticket.source_owner}</td>
                  </tr>
                  <tr>
                    <td>Tiêu đề</td>
                    <td>{ticket.title}</td>
                  </tr>
                  <tr>
                    <td>Mô tả</td>
                    <td>{ticket.description || "—"}</td>
                  </tr>
                  <tr>
                    <td>Người mở ticket</td>
                    <td>{ticket.opened_by || "—"}</td>
                  </tr>
                  <tr>
                    <td>Thời điểm mở</td>
                    <td>{formatTime(ticket.opened_at)}</td>
                  </tr>
                  <tr>
                    <td>Đã thông báo chủ quản nguồn</td>
                    <td>{ticket.notified ? "Có" : "Không"}</td>
                  </tr>
                  {isClosed && (
                    <>
                      <tr>
                        <td>Người đóng ticket</td>
                        <td>{ticket.closed_by}</td>
                      </tr>
                      <tr>
                        <td>Thời điểm đóng</td>
                        <td>{formatTime(ticket.closed_at)}</td>
                      </tr>
                      <tr>
                        <td>Ghi chú khi đóng</td>
                        <td>{ticket.close_note || "—"}</td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bước 2: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Bước 2 — Cập nhật tiến độ xử lý ({ticket.history.length})</h2>
            </div>
            <div className="card-body">
              {!isClosed && (
                <form onSubmit={handleAddProgress} style={{ marginBottom: 16 }}>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="progress_note">Nội dung cập nhật</label>
                      <input
                        id="progress_note"
                        value={progressNote}
                        onChange={(e) => setProgressNote(e.target.value)}
                        placeholder="vd: Đã liên hệ chủ quản nguồn, đang chờ xác nhận"
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="progress_status">Chuyển trạng thái</label>
                      <select
                        id="progress_status"
                        value={progressStatus}
                        onChange={(e) => setProgressStatus(e.target.value)}
                      >
                        <option value="OPEN">Mở</option>
                        <option value="IN_PROGRESS">Đang xử lý</option>
                        <option value="RESOLVED">Đã xử lý (chờ đóng)</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="progress_updated_by">Người cập nhật</label>
                      <input
                        id="progress_updated_by"
                        value={progressUpdatedBy}
                        onChange={(e) => setProgressUpdatedBy(e.target.value)}
                        required
                      />
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-end" }}>
                      <button type="submit" className="btn btn-primary" disabled={updating}>
                        <PlusCircle size={15} />
                        {updating ? "Đang lưu..." : "Cập nhật tiến độ"}
                      </button>
                    </div>
                  </div>
                </form>
              )}

              {ticket.history.length === 0 ? (
                <div className="empty-state">Chưa có lịch sử cập nhật tiến độ nào.</div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Nội dung</th>
                      <th>Người cập nhật</th>
                      <th>Trạng thái</th>
                      <th>Thời điểm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ticket.history.map((h, idx) => (
                      <tr key={idx}>
                        <td>{idx}</td>
                        <td>{h.note}</td>
                        <td>{h.updated_by}</td>
                        <td>
                          <span className={`badge ${STATUS_BADGE[h.status] || "badge-neutral"}`}>
                            {STATUS_LABEL[h.status] || h.status}
                          </span>
                        </td>
                        <td>{formatTime(h.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Bước 3: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký */}
          <div className="card">
            <div className="card-header">
              <h2>Bước 3 — Đóng ticket khi resolved</h2>
            </div>
            <div className="card-body">
              {isClosed ? (
                <div className="alert alert-success">
                  <CheckCircle2 size={16} />
                  <span>Ticket đã đóng — hệ thống đã cập nhật trạng thái CLOSED + ghi nhật ký.</span>
                </div>
              ) : (
                <>
                  {!isResolved && (
                    <div className="alert alert-error" style={{ marginBottom: 12 }}>
                      <AlertCircle size={16} />
                      <span>
                        Chưa thể đóng: ticket cần được cập nhật sang trạng thái "Đã xử lý (chờ
                        đóng)" ở bước 2 trước.
                      </span>
                    </div>
                  )}
                  <form onSubmit={handleClose}>
                    <div className="form-grid">
                      <div className="field">
                        <label htmlFor="closed_by">Người đóng ticket</label>
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
                          placeholder="vd: Chủ quản nguồn đã xác nhận và bổ sung dữ liệu"
                        />
                      </div>
                      <div style={{ display: "flex", alignItems: "flex-end" }}>
                        <button
                          type="submit"
                          className="btn btn-primary"
                          disabled={closing || !isResolved}
                        >
                          <Lock size={15} />
                          {closing ? "Đang đóng..." : "Đóng ticket"}
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