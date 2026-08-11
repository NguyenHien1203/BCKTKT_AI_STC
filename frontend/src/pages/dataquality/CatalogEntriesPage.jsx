import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  History,
  Landmark,
  Package,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  approveCatalogChangeRequest,
  createCatalogEntry,
  listCatalogChangeRequests,
  listCatalogEntries,
  listCatalogEntryVersions,
  proposeCatalogEntryChange,
  rejectCatalogChangeRequest,
  updateCatalogEntry,
} from "../../api/catalogEntries.js";

const CATALOG_TABS = [
  { type: "ITEM", label: "Mặt hàng", icon: Package },
  { type: "DOCUMENT_TYPE", label: "Loại văn bản", icon: FileText },
  { type: "FUNDING_SOURCE", label: "Nguồn vốn", icon: Landmark },
];

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_CREATE_FORM = {
  code: "",
  name: "",
  unit: "",
  description: "",
  is_sensitive: false,
  effective_from: "",
  note: "",
};
const EMPTY_EDIT_FORM = { name: "", unit: "", description: "", status: "ACTIVE", note: "" };
const EMPTY_PROPOSE_FORM = {
  requested_by: "",
  reason: "",
  proposed_name: "",
  proposed_unit: "",
  proposed_description: "",
  proposed_status: "",
};
const EMPTY_REVIEW = { reviewed_by: "", review_note: "" };

export default function CatalogEntriesPage() {
  const [catalogType, setCatalogType] = useState("ITEM");
  const [entries, setEntries] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [changeRequests, setChangeRequests] = useState([]);
  const [activePanel, setActivePanel] = useState("create"); // create | edit | propose

  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);
  const [proposeForm, setProposeForm] = useState(EMPTY_PROPOSE_FORM);
  const [reviewNote, setReviewNote] = useState(EMPTY_REVIEW);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedEntry = entries.find((e) => e.id === selectedId) || null;

  async function loadEntries(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listCatalogEntries({
        catalogType,
        status: statusFilter || null,
      });
      setEntries(data);
      if (!keepSelection || !data.some((e) => e.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(entryId) {
    if (!entryId) {
      setVersions([]);
      setChangeRequests([]);
      return;
    }
    try {
      const [v, r] = await Promise.all([
        listCatalogEntryVersions(entryId),
        listCatalogChangeRequests({ entryId }),
      ]);
      setVersions(v);
      setChangeRequests(r);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    setSelectedId(null);
    loadEntries(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogType, statusFilter]);

  useEffect(() => {
    loadDetail(selectedId);
    if (selectedEntry) {
      setEditForm({
        name: selectedEntry.name,
        unit: selectedEntry.unit || "",
        description: selectedEntry.description || "",
        status: selectedEntry.status,
        note: "",
      });
      setActivePanel(selectedEntry.is_sensitive ? "propose" : "edit");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await createCatalogEntry({
        catalogType,
        code: createForm.code.trim(),
        name: createForm.name.trim(),
        unit: createForm.unit.trim() || null,
        description: createForm.description.trim() || null,
        isSensitive: createForm.is_sensitive,
        effectiveFrom: createForm.effective_from || null,
        note: createForm.note.trim() || null,
      });
      setInfo(`Đã thêm mục "${created.code}" (phiên bản ${created.version}).`);
      setError(null);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadEntries(false);
      setSelectedId(created.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!selectedEntry) return;
    setSubmitting(true);
    try {
      const updated = await updateCatalogEntry(selectedEntry.id, {
        name: editForm.name.trim() || null,
        unit: editForm.unit.trim(),
        description: editForm.description.trim(),
        status: editForm.status || null,
        note: editForm.note.trim() || null,
      });
      setInfo(`Đã sửa mục "${updated.code}" -- phiên bản mới: ${updated.version}.`);
      setError(null);
      setEditForm((f) => ({ ...f, note: "" }));
      await loadEntries(true);
      await loadDetail(selectedEntry.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePropose(e) {
    e.preventDefault();
    if (!selectedEntry) return;
    setSubmitting(true);
    try {
      await proposeCatalogEntryChange(selectedEntry.id, {
        requestedBy: proposeForm.requested_by,
        reason: proposeForm.reason,
        proposedName: proposeForm.proposed_name || null,
        proposedUnit: proposeForm.proposed_unit || null,
        proposedDescription: proposeForm.proposed_description || null,
        proposedStatus: proposeForm.proposed_status || null,
      });
      setInfo("Đã lưu yêu cầu thay đổi -- chờ người có thẩm quyền duyệt (UC-037).");
      setError(null);
      setProposeForm(EMPTY_PROPOSE_FORM);
      await loadDetail(selectedEntry.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(requestId) {
    if (!reviewNote.reviewed_by.trim()) {
      setError("Vui lòng nhập người duyệt trước khi duyệt yêu cầu.");
      return;
    }
    try {
      await approveCatalogChangeRequest(requestId, {
        reviewedBy: reviewNote.reviewed_by,
        reviewNote: reviewNote.review_note || null,
      });
      setInfo("Đã duyệt -- thay đổi được áp dụng vào danh mục.");
      setError(null);
      setReviewNote(EMPTY_REVIEW);
      await loadEntries(true);
      await loadDetail(selectedEntry.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    }
  }

  async function handleReject(requestId) {
    if (!reviewNote.reviewed_by.trim()) {
      setError("Vui lòng nhập người duyệt trước khi từ chối yêu cầu.");
      return;
    }
    try {
      await rejectCatalogChangeRequest(requestId, {
        reviewedBy: reviewNote.reviewed_by,
        reviewNote: reviewNote.review_note || null,
      });
      setInfo("Đã từ chối yêu cầu thay đổi.");
      setError(null);
      setReviewNote(EMPTY_REVIEW);
      await loadDetail(selectedEntry.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    }
  }

  return (
    <AppLayout
      title="Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn"
      subtitle="UC-036 — Xem từng danh mục (mặt hàng/loại văn bản/nguồn vốn); thêm/sửa entry (hệ thống quản lý phiên bản); đề nghị thay đổi danh mục nhạy cảm (hệ thống lưu yêu cầu chờ duyệt)."
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

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {CATALOG_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.type}
              className={`btn ${catalogType === tab.type ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setCatalogType(tab.type)}
            >
              <Icon size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 1: Xem danh mục ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              Bước 1 — Danh mục{" "}
              {CATALOG_TABS.find((t) => t.type === catalogType)?.label.toLowerCase()}
            </h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadEntries(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="status-filter">Trạng thái</label>
                <select
                  id="status-filter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  <option value="ACTIVE">Đang hoạt động</option>
                  <option value="CLOSED">Đã đóng</option>
                </select>
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : entries.length === 0 ? (
              <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có mục nào.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Tên</th>
                    <th>Trạng thái</th>
                    <th>Nhạy cảm</th>
                    <th>Phiên bản</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((en) => (
                    <tr
                      key={en.id}
                      onClick={() => setSelectedId(en.id)}
                      style={{
                        cursor: "pointer",
                        background:
                          selectedId === en.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
                      }}
                    >
                      <td>
                        <strong>{en.code}</strong>
                      </td>
                      <td>{en.name}</td>
                      <td>
                        <span
                          className={`badge ${en.status === "ACTIVE" ? "badge-success" : "badge-danger"}`}
                        >
                          {en.status === "ACTIVE" ? "Đang hoạt động" : "Đã đóng"}
                        </span>
                      </td>
                      <td>
                        {en.is_sensitive ? (
                          <span className="badge badge-warning">
                            <ShieldAlert size={12} style={{ verticalAlign: "middle" }} /> Nhạy cảm
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>v{en.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Bước 2 & 3: Thao tác ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              {selectedEntry ? `${selectedEntry.code} — ${selectedEntry.name}` : "Thêm mục mới"}
            </h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button
                className={`btn ${activePanel === "create" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("create")}
              >
                Thêm mới
              </button>
              <button
                className={`btn ${activePanel === "edit" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("edit")}
                disabled={!selectedEntry || selectedEntry.is_sensitive}
                title={
                  selectedEntry?.is_sensitive
                    ? "Mục nhạy cảm -- vui lòng dùng \"Đề nghị thay đổi\""
                    : undefined
                }
              >
                Sửa entry
              </button>
              <button
                className={`btn ${activePanel === "propose" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("propose")}
                disabled={!selectedEntry}
              >
                <ShieldAlert size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Đề nghị thay đổi nhạy cảm
              </button>
            </div>

            {activePanel === "create" && (
              <form onSubmit={handleCreate} className="form-grid">
                <div className="field">
                  <label htmlFor="c-code">Mã *</label>
                  <input
                    id="c-code"
                    required
                    value={createForm.code}
                    onChange={(e) => setCreateForm((f) => ({ ...f, code: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-name">Tên *</label>
                  <input
                    id="c-name"
                    required
                    value={createForm.name}
                    onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </div>
                {catalogType === "ITEM" && (
                  <div className="field">
                    <label htmlFor="c-unit">Đơn vị tính</label>
                    <input
                      id="c-unit"
                      placeholder="Cái / Bộ / Kg ..."
                      value={createForm.unit}
                      onChange={(e) => setCreateForm((f) => ({ ...f, unit: e.target.value }))}
                    />
                  </div>
                )}
                <div className="field">
                  <label htmlFor="c-effective">Hiệu lực từ (tuỳ chọn)</label>
                  <input
                    id="c-effective"
                    type="date"
                    value={createForm.effective_from}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, effective_from: e.target.value }))
                    }
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="c-desc">Mô tả</label>
                  <input
                    id="c-desc"
                    value={createForm.description}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-sensitive" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      id="c-sensitive"
                      type="checkbox"
                      checked={createForm.is_sensitive}
                      onChange={(e) =>
                        setCreateForm((f) => ({ ...f, is_sensitive: e.target.checked }))
                      }
                    />
                    Mục nhạy cảm (sửa sau phải qua đề nghị chờ duyệt)
                  </label>
                </div>
                <div className="field field-full">
                  <label htmlFor="c-note">Ghi chú</label>
                  <input
                    id="c-note"
                    value={createForm.note}
                    onChange={(e) => setCreateForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? "Đang lưu..." : "Thêm mục"}
                  </button>
                </div>
              </form>
            )}

            {activePanel === "edit" && selectedEntry && !selectedEntry.is_sensitive && (
              <form onSubmit={handleUpdate} className="form-grid">
                <div className="field">
                  <label htmlFor="e-name">Tên</label>
                  <input
                    id="e-name"
                    value={editForm.name}
                    onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </div>
                {catalogType === "ITEM" && (
                  <div className="field">
                    <label htmlFor="e-unit">Đơn vị tính</label>
                    <input
                      id="e-unit"
                      value={editForm.unit}
                      onChange={(e) => setEditForm((f) => ({ ...f, unit: e.target.value }))}
                    />
                  </div>
                )}
                <div className="field">
                  <label htmlFor="e-status">Trạng thái</label>
                  <select
                    id="e-status"
                    value={editForm.status}
                    onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}
                  >
                    <option value="ACTIVE">Đang hoạt động</option>
                    <option value="CLOSED">Đã đóng</option>
                  </select>
                </div>
                <div className="field field-full">
                  <label htmlFor="e-desc">Mô tả</label>
                  <input
                    id="e-desc"
                    value={editForm.description}
                    onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="e-note">Ghi chú thay đổi</label>
                  <input
                    id="e-note"
                    value={editForm.note}
                    onChange={(e) => setEditForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? "Đang lưu..." : `Lưu (tạo phiên bản v${selectedEntry.version + 1})`}
                  </button>
                </div>
              </form>
            )}

            {activePanel === "propose" && selectedEntry && (
              <div>
                {!selectedEntry.is_sensitive && (
                  <div className="alert alert-info" style={{ marginBottom: 12 }}>
                    Mục này chưa đánh dấu nhạy cảm -- vẫn có thể gửi đề nghị, nhưng hệ thống sẽ từ
                    chối (422) vì bước 3 chỉ áp dụng cho mục nhạy cảm; vui lòng dùng "Sửa entry".
                  </div>
                )}
                <form onSubmit={handlePropose} className="form-grid">
                  <div className="field">
                    <label htmlFor="p-by">Người đề nghị *</label>
                    <input
                      id="p-by"
                      required
                      value={proposeForm.requested_by}
                      onChange={(e) =>
                        setProposeForm({ ...proposeForm, requested_by: e.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="p-name">Đề nghị đổi tên</label>
                    <input
                      id="p-name"
                      value={proposeForm.proposed_name}
                      onChange={(e) =>
                        setProposeForm({ ...proposeForm, proposed_name: e.target.value })
                      }
                    />
                  </div>
                  {catalogType === "ITEM" && (
                    <div className="field">
                      <label htmlFor="p-unit">Đề nghị đổi đơn vị tính</label>
                      <input
                        id="p-unit"
                        value={proposeForm.proposed_unit}
                        onChange={(e) =>
                          setProposeForm({ ...proposeForm, proposed_unit: e.target.value })
                        }
                      />
                    </div>
                  )}
                  <div className="field">
                    <label htmlFor="p-status">Đề nghị đổi trạng thái</label>
                    <select
                      id="p-status"
                      value={proposeForm.proposed_status}
                      onChange={(e) =>
                        setProposeForm({ ...proposeForm, proposed_status: e.target.value })
                      }
                    >
                      <option value="">-- Không đổi --</option>
                      <option value="ACTIVE">Đang hoạt động</option>
                      <option value="CLOSED">Đã đóng</option>
                    </select>
                  </div>
                  <div className="field field-full">
                    <label htmlFor="p-desc">Đề nghị đổi mô tả</label>
                    <input
                      id="p-desc"
                      value={proposeForm.proposed_description}
                      onChange={(e) =>
                        setProposeForm({ ...proposeForm, proposed_description: e.target.value })
                      }
                    />
                  </div>
                  <div className="field field-full">
                    <label htmlFor="p-reason">Lý do đề nghị *</label>
                    <input
                      id="p-reason"
                      required
                      value={proposeForm.reason}
                      onChange={(e) => setProposeForm({ ...proposeForm, reason: e.target.value })}
                    />
                  </div>
                  <div className="field field-full">
                    <button
                      className="btn btn-primary"
                      type="submit"
                      disabled={
                        submitting ||
                        !proposeForm.requested_by.trim() ||
                        !proposeForm.reason.trim() ||
                        (!proposeForm.proposed_name.trim() &&
                          !proposeForm.proposed_unit.trim() &&
                          !proposeForm.proposed_description.trim() &&
                          !proposeForm.proposed_status)
                      }
                    >
                      {submitting ? "Đang gửi..." : "Gửi đề nghị thay đổi (bước 3)"}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {selectedEntry && (
              <>
                <h3 style={{ marginTop: 24, fontSize: 14 }}>
                  <Clock size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                  Yêu cầu chờ duyệt / lịch sử duyệt
                </h3>
                {changeRequests.length === 0 ? (
                  <div className="empty-state">Chưa có yêu cầu thay đổi nào.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {changeRequests.map((r) => (
                      <div
                        key={r.id}
                        style={{
                          border: "1px solid var(--color-border, #eee)",
                          borderRadius: 6,
                          padding: 10,
                        }}
                      >
                        <div
                          style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}
                        >
                          <span>
                            <strong>{r.requested_by}</strong> đề nghị lúc {formatTime(r.created_at)}
                          </span>
                          <span
                            className={`badge ${
                              r.status === "PENDING"
                                ? "badge-warning"
                                : r.status === "APPROVED"
                                  ? "badge-success"
                                  : "badge-danger"
                            }`}
                          >
                            {r.status}
                          </span>
                        </div>
                        <div style={{ fontSize: 13, marginBottom: 4 }}>Lý do: {r.reason}</div>
                        {r.proposed_name && (
                          <div style={{ fontSize: 13 }}>Đề nghị đổi tên: {r.proposed_name}</div>
                        )}
                        {r.proposed_unit && (
                          <div style={{ fontSize: 13 }}>
                            Đề nghị đổi đơn vị tính: {r.proposed_unit}
                          </div>
                        )}
                        {r.proposed_description && (
                          <div style={{ fontSize: 13 }}>
                            Đề nghị đổi mô tả: {r.proposed_description}
                          </div>
                        )}
                        {r.proposed_status && (
                          <div style={{ fontSize: 13 }}>
                            Đề nghị đổi trạng thái: {r.proposed_status}
                          </div>
                        )}
                        {r.status !== "PENDING" && (
                          <div
                            style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}
                          >
                            Đã xử lý bởi {r.reviewed_by} lúc {formatTime(r.reviewed_at)}
                            {r.review_note ? ` — ${r.review_note}` : ""}
                          </div>
                        )}
                        {r.status === "PENDING" && (
                          <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
                            <div className="field" style={{ flex: "1 1 160px", marginBottom: 0 }}>
                              <label htmlFor={`reviewed-by-${r.id}`}>Người duyệt</label>
                              <input
                                id={`reviewed-by-${r.id}`}
                                type="text"
                                placeholder="Người duyệt"
                                value={reviewNote.reviewed_by}
                                onChange={(e) =>
                                  setReviewNote({ ...reviewNote, reviewed_by: e.target.value })
                                }
                              />
                            </div>
                            <div className="field" style={{ flex: "1 1 160px", marginBottom: 0 }}>
                              <label htmlFor={`review-note-${r.id}`}>Ghi chú duyệt</label>
                              <input
                                id={`review-note-${r.id}`}
                                type="text"
                                placeholder="Ghi chú duyệt"
                                value={reviewNote.review_note}
                                onChange={(e) =>
                                  setReviewNote({ ...reviewNote, review_note: e.target.value })
                                }
                              />
                            </div>
                            <button className="btn btn-primary" onClick={() => handleApprove(r.id)}>
                              Duyệt
                            </button>
                            <button className="btn btn-secondary" onClick={() => handleReject(r.id)}>
                              Từ chối
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <History size={16} /> Lịch sử phiên bản
                </h3>
                {versions.length === 0 ? (
                  <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có lịch sử.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Phiên bản</th>
                        <th>Tên</th>
                        <th>Trạng thái</th>
                        <th>Ghi chú</th>
                        <th>Thời điểm</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id}>
                          <td>v{v.version}</td>
                          <td>{v.name}</td>
                          <td>{v.status === "ACTIVE" ? "Đang hoạt động" : "Đã đóng"}</td>
                          <td>{v.change_note || "—"}</td>
                          <td>{formatTime(v.changed_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}