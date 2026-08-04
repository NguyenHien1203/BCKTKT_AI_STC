import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  History,
  Landmark,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  approveBudgetItemChange,
  createBudgetItem,
  getBudgetItemTree,
  listBudgetItemChangeRequests,
  listBudgetItemVersions,
  proposeBudgetItemChange,
  rejectBudgetItemChange,
  updateBudgetItem,
} from "../../api/budgetItemCatalog.js";

const LEVEL_LABEL = {
  CHUONG: "Chương",
  LOAI: "Loại",
  KHOAN: "Khoản",
  MUC: "Mục",
  TIEU_MUC: "Tiểu mục",
};
const LEVELS = ["CHUONG", "LOAI", "KHOAN", "MUC", "TIEU_MUC"];
const CURRENT_YEAR = new Date().getFullYear();

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function flattenTree(nodes, acc = []) {
  for (const n of nodes) {
    acc.push(n.item);
    flattenTree(n.children, acc);
  }
  return acc;
}

const EMPTY_CREATE_FORM = {
  code: "",
  name: "",
  level: "CHUONG",
  parent_id: "",
  is_sensitive: false,
  effective_from: "",
  note: "",
};
const EMPTY_EDIT_FORM = { name: "", status: "ACTIVE", note: "" };
const EMPTY_PROPOSE_FORM = {
  requested_by: "",
  reason: "",
  proposed_name: "",
  proposed_status: "",
};
const EMPTY_REVIEW_NOTE = { reviewed_by: "", review_note: "" };

function TreeNode({ node, depth, expanded, onToggle, selectedId, onSelect }) {
  const item = node.item;
  const isExpanded = expanded.has(item.id);
  const hasChildren = node.children.length > 0;

  return (
    <>
      <div
        className={`org-tree-row ${selectedId === item.id ? "org-tree-row-active" : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 8px",
          paddingLeft: 8 + depth * 20,
          borderBottom: "1px solid var(--color-border, #eee)",
          cursor: "pointer",
          background: selectedId === item.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
        }}
        onClick={() => onSelect(item.id)}
      >
        <span
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(item.id);
          }}
          style={{ width: 16, display: "inline-flex", justifyContent: "center", color: "var(--color-text-secondary, #888)" }}
        >
          {hasChildren ? isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} /> : null}
        </span>
        <span className="badge badge-neutral">{LEVEL_LABEL[item.level] || item.level}</span>
        <strong>{item.code}</strong>
        <span>{item.name}</span>
        {item.is_sensitive && (
          <span className="badge badge-warning" title="Khoản mục nhạy cảm -- sửa phải qua đề nghị chờ duyệt">
            <ShieldAlert size={12} style={{ verticalAlign: "middle", marginRight: 2 }} />
            Nhạy cảm
          </span>
        )}
        <span className={`badge ${item.status === "ACTIVE" ? "badge-success" : "badge-danger"}`}>
          {item.status === "ACTIVE" ? "Đang hoạt động" : "Đã đóng"}
        </span>
        <span style={{ color: "var(--color-text-secondary, #888)", fontSize: 12 }}>v{item.version}</span>
      </div>
      {hasChildren && isExpanded
        ? node.children.map((c) => (
            <TreeNode
              key={c.item.id}
              node={c}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))
        : null}
    </>
  );
}

export default function BudgetItemCatalogPage() {
  const [budgetYear, setBudgetYear] = useState(CURRENT_YEAR);
  const [tree, setTree] = useState([]);
  const [includeClosed, setIncludeClosed] = useState(true);
  const [expanded, setExpanded] = useState(new Set());
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [changeRequests, setChangeRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const [activePanel, setActivePanel] = useState("create"); // create | edit | propose
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);
  const [proposeForm, setProposeForm] = useState(EMPTY_PROPOSE_FORM);
  const [reviewNote, setReviewNote] = useState(EMPTY_REVIEW_NOTE);
  const [submitting, setSubmitting] = useState(false);

  const flatItems = useMemo(() => flattenTree(tree), [tree]);
  const selectedItem = useMemo(
    () => flatItems.find((i) => i.id === selectedId) || null,
    [flatItems, selectedId],
  );

  async function loadTree() {
    setLoading(true);
    try {
      const data = await getBudgetItemTree({ budgetYear, includeClosed });
      setTree(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(itemId) {
    try {
      setVersions(await listBudgetItemVersions(itemId));
    } catch {
      setVersions([]);
    }
  }

  async function loadChangeRequests(itemId) {
    try {
      setChangeRequests(await listBudgetItemChangeRequests({ itemId }));
    } catch {
      setChangeRequests([]);
    }
  }

  useEffect(() => {
    loadTree();
    setSelectedId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [budgetYear, includeClosed]);

  useEffect(() => {
    if (selectedItem) {
      setEditForm({ name: selectedItem.name, status: selectedItem.status, note: "" });
      setProposeForm(EMPTY_PROPOSE_FORM);
      loadVersions(selectedItem.id);
      loadChangeRequests(selectedItem.id);
      setActivePanel(selectedItem.is_sensitive ? "propose" : "edit");
    } else {
      setVersions([]);
      setChangeRequests([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function toggleExpand(id) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function reportError(e) {
    setError(e?.response?.data?.detail?.message || e.message);
    setInfo(null);
  }

  function reportSuccess(message) {
    setInfo(message);
    setError(null);
  }

  // ---------- Bước 2: Thêm entry ----------
  async function handleCreate() {
    setSubmitting(true);
    try {
      const item = await createBudgetItem({
        code: createForm.code.trim(),
        name: createForm.name.trim(),
        level: createForm.level,
        budgetYear,
        parentId: createForm.parent_id ? Number(createForm.parent_id) : null,
        isSensitive: createForm.is_sensitive,
        effectiveFrom: createForm.effective_from || null,
        note: createForm.note || null,
      });
      reportSuccess(`Đã thêm khoản mục "${item.code}" (phiên bản 1, năm ngân sách ${budgetYear}).`);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadTree();
      setSelectedId(item.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 2: Sửa entry (chỉ khoản mục KHÔNG nhạy cảm) ----------
  async function handleUpdate() {
    if (!selectedItem) return;
    setSubmitting(true);
    try {
      const updated = await updateBudgetItem(selectedItem.id, {
        name: editForm.name,
        status: editForm.status,
        note: editForm.note || null,
      });
      reportSuccess(`Đã lưu khoản mục "${updated.code}" (phiên bản ${updated.version}).`);
      await loadTree();
      await loadVersions(updated.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 3: Đề nghị thay đổi khoản mục nhạy cảm ----------
  async function handlePropose() {
    if (!selectedItem) return;
    setSubmitting(true);
    try {
      await proposeBudgetItemChange(selectedItem.id, {
        requestedBy: proposeForm.requested_by,
        reason: proposeForm.reason,
        proposedName: proposeForm.proposed_name || null,
        proposedStatus: proposeForm.proposed_status || null,
      });
      reportSuccess("Đã gửi đề nghị thay đổi -- hệ thống lưu yêu cầu chờ duyệt.");
      setProposeForm(EMPTY_PROPOSE_FORM);
      await loadChangeRequests(selectedItem.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(requestId) {
    setSubmitting(true);
    try {
      const updated = await approveBudgetItemChange(requestId, {
        reviewedBy: reviewNote.reviewed_by || "quan-tri-danh-muc",
        reviewNote: reviewNote.review_note || null,
      });
      reportSuccess(`Đã duyệt -- khoản mục "${updated.code}" cập nhật lên phiên bản ${updated.version}.`);
      setReviewNote(EMPTY_REVIEW_NOTE);
      await loadTree();
      await loadVersions(updated.id);
      await loadChangeRequests(selectedItem.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReject(requestId) {
    setSubmitting(true);
    try {
      await rejectBudgetItemChange(requestId, {
        reviewedBy: reviewNote.reviewed_by || "quan-tri-danh-muc",
        reviewNote: reviewNote.review_note || null,
      });
      reportSuccess("Đã từ chối yêu cầu thay đổi.");
      setReviewNote(EMPTY_REVIEW_NOTE);
      await loadChangeRequests(selectedItem.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý danh mục khoản mục NSNN"
      subtitle="UC-034 — Xem cây khoản mục NSNN (Chương/Loại/Khoản/Mục/Tiểu mục) theo năm ngân sách; thêm/sửa entry (hệ thống quản lý phiên bản theo năm); đề nghị thay đổi khoản mục nhạy cảm (hệ thống lưu yêu cầu chờ duyệt)."
    >
      {error && (
        <div className="alert alert-error">
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

      <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 1fr) minmax(360px, 1fr)", gap: 20 }}>
        {/* ---------- Bước 1: Xem cây khoản mục NSNN ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              <Landmark size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Bước 1 — Cây khoản mục NSNN
            </h2>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
                Năm NS:
                <input
                  type="number"
                  value={budgetYear}
                  onChange={(e) => setBudgetYear(Number(e.target.value) || CURRENT_YEAR)}
                  style={{ width: 80 }}
                />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={includeClosed}
                  onChange={(e) => setIncludeClosed(e.target.checked)}
                />
                Gồm đã đóng
              </label>
              <button className="icon-btn" title="Làm mới" onClick={loadTree}>
                <RefreshCw size={15} />
              </button>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {loading ? (
              <div className="empty-state">Đang tải dữ liệu...</div>
            ) : tree.length === 0 ? (
              <div className="empty-state">Danh mục khoản mục NSNN năm {budgetYear} chưa có dữ liệu.</div>
            ) : (
              <div style={{ maxHeight: 560, overflowY: "auto" }}>
                {tree.map((n) => (
                  <TreeNode
                    key={n.item.id}
                    node={n}
                    depth={0}
                    expanded={expanded}
                    onToggle={toggleExpand}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ---------- Panel thao tác ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>{selectedItem ? `Khoản mục: ${selectedItem.code}` : "Thêm khoản mục mới"}</h2>
            {selectedItem && (
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  className={`btn ${activePanel === "edit" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActivePanel("edit")}
                >
                  Sửa
                </button>
                <button
                  className={`btn ${activePanel === "propose" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActivePanel("propose")}
                >
                  Đề nghị thay đổi
                </button>
                <button
                  className={`btn ${activePanel === "create" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActivePanel("create")}
                >
                  Thêm mới
                </button>
              </div>
            )}
          </div>
          <div className="card-body">
            {activePanel === "create" && (
              <div className="form-grid">
                <div className="field">
                  <label>Mã khoản mục (code)</label>
                  <input
                    type="text"
                    value={createForm.code}
                    onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Tên khoản mục</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Cấp</label>
                  <select
                    value={createForm.level}
                    onChange={(e) => setCreateForm({ ...createForm, level: e.target.value })}
                  >
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>
                        {LEVEL_LABEL[l]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Khoản mục cha (id, để trống = gốc)</label>
                  <input
                    type="text"
                    value={createForm.parent_id}
                    placeholder={selectedItem ? `vd: ${selectedItem.id}` : ""}
                    onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Hiệu lực từ</label>
                  <input
                    type="date"
                    value={createForm.effective_from}
                    onChange={(e) => setCreateForm({ ...createForm, effective_from: e.target.value })}
                  />
                </div>
                <div className="field" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={createForm.is_sensitive}
                    onChange={(e) => setCreateForm({ ...createForm, is_sensitive: e.target.checked })}
                  />
                  <label style={{ margin: 0 }}>Khoản mục nhạy cảm</label>
                </div>
                <div className="field">
                  <label>Ghi chú</label>
                  <input
                    type="text"
                    value={createForm.note}
                    onChange={(e) => setCreateForm({ ...createForm, note: e.target.value })}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  disabled={submitting || !createForm.code.trim() || !createForm.name.trim()}
                  onClick={handleCreate}
                >
                  {submitting ? "Đang lưu..." : `Thêm khoản mục (bước 2, năm ${budgetYear})`}
                </button>
              </div>
            )}

            {activePanel === "edit" && selectedItem && (
              <div className="form-grid">
                {selectedItem.is_sensitive ? (
                  <p style={{ gridColumn: "1 / -1", color: "var(--color-danger)" }}>
                    <ShieldAlert size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    Đây là khoản mục nhạy cảm -- không thể sửa trực tiếp. Vui lòng dùng tab
                    "Đề nghị thay đổi".
                  </p>
                ) : (
                  <>
                    <div className="field">
                      <label>Tên khoản mục</label>
                      <input
                        type="text"
                        value={editForm.name}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Trạng thái</label>
                      <select
                        value={editForm.status}
                        onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                      >
                        <option value="ACTIVE">Đang hoạt động</option>
                        <option value="CLOSED">Đã đóng</option>
                      </select>
                    </div>
                    <div className="field">
                      <label>Ghi chú thay đổi</label>
                      <input
                        type="text"
                        value={editForm.note}
                        onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                      />
                    </div>
                    <button
                      className="btn btn-primary"
                      disabled={submitting || selectedItem.status === "CLOSED"}
                      onClick={handleUpdate}
                    >
                      {submitting ? "Đang lưu..." : "Lưu thay đổi (bước 2)"}
                    </button>
                  </>
                )}
              </div>
            )}

            {activePanel === "propose" && selectedItem && (
              <div>
                {!selectedItem.is_sensitive && (
                  <p style={{ color: "var(--color-text-secondary)", fontSize: 13, marginBottom: 12 }}>
                    Khoản mục này không phải khoản mục nhạy cảm -- có thể sửa trực tiếp ở tab
                    "Sửa". Chức năng đề nghị thay đổi chỉ áp dụng cho khoản mục nhạy cảm.
                  </p>
                )}
                {selectedItem.is_sensitive && (
                  <div className="form-grid" style={{ marginBottom: 16 }}>
                    <div className="field">
                      <label>Người đề nghị</label>
                      <input
                        type="text"
                        value={proposeForm.requested_by}
                        onChange={(e) => setProposeForm({ ...proposeForm, requested_by: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Tên đề nghị đổi thành (tuỳ chọn)</label>
                      <input
                        type="text"
                        value={proposeForm.proposed_name}
                        onChange={(e) => setProposeForm({ ...proposeForm, proposed_name: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Trạng thái đề nghị đổi thành (tuỳ chọn)</label>
                      <select
                        value={proposeForm.proposed_status}
                        onChange={(e) => setProposeForm({ ...proposeForm, proposed_status: e.target.value })}
                      >
                        <option value="">(giữ nguyên)</option>
                        <option value="ACTIVE">Đang hoạt động</option>
                        <option value="CLOSED">Đã đóng</option>
                      </select>
                    </div>
                    <div className="field">
                      <label>Lý do đề nghị</label>
                      <input
                        type="text"
                        value={proposeForm.reason}
                        onChange={(e) => setProposeForm({ ...proposeForm, reason: e.target.value })}
                      />
                    </div>
                    <button
                      className="btn btn-primary"
                      disabled={
                        submitting ||
                        !proposeForm.requested_by.trim() ||
                        !proposeForm.reason.trim() ||
                        (!proposeForm.proposed_name.trim() && !proposeForm.proposed_status)
                      }
                      onClick={handlePropose}
                    >
                      {submitting ? "Đang gửi..." : "Gửi đề nghị thay đổi (bước 3)"}
                    </button>
                  </div>
                )}

                <h3 style={{ fontSize: 14 }}>
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
                        style={{ border: "1px solid var(--color-border, #eee)", borderRadius: 6, padding: 10 }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
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
                        {r.proposed_status && (
                          <div style={{ fontSize: 13 }}>Đề nghị đổi trạng thái: {r.proposed_status}</div>
                        )}
                        {r.status !== "PENDING" && (
                          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                            Đã xử lý bởi {r.reviewed_by} lúc {formatTime(r.reviewed_at)}
                            {r.review_note ? ` — ${r.review_note}` : ""}
                          </div>
                        )}
                        {r.status === "PENDING" && (
                          <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
                            <input
                              type="text"
                              placeholder="Người duyệt"
                              value={reviewNote.reviewed_by}
                              onChange={(e) => setReviewNote({ ...reviewNote, reviewed_by: e.target.value })}
                              style={{ flex: 1 }}
                            />
                            <input
                              type="text"
                              placeholder="Ghi chú duyệt"
                              value={reviewNote.review_note}
                              onChange={(e) => setReviewNote({ ...reviewNote, review_note: e.target.value })}
                              style={{ flex: 1 }}
                            />
                            <button
                              className="btn btn-primary"
                              disabled={submitting}
                              onClick={() => handleApprove(r.id)}
                            >
                              <CheckCircle2 size={14} /> Duyệt
                            </button>
                            <button
                              className="btn-danger-ghost"
                              disabled={submitting}
                              onClick={() => handleReject(r.id)}
                            >
                              <XCircle size={14} /> Từ chối
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {selectedItem && (
              <div style={{ marginTop: 20 }}>
                <h3 style={{ fontSize: 14 }}>
                  <History size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                  Lịch sử phiên bản (năm ngân sách {selectedItem.budget_year})
                </h3>
                {versions.length === 0 ? (
                  <div className="empty-state">Chưa có lịch sử phiên bản.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Phiên bản</th>
                        <th>Tên</th>
                        <th>Trạng thái</th>
                        <th>Nhạy cảm</th>
                        <th>Ghi chú</th>
                        <th>Thời điểm</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id}>
                          <td>{v.version}</td>
                          <td>{v.name}</td>
                          <td>{v.status}</td>
                          <td>{v.is_sensitive ? "Có" : "Không"}</td>
                          <td>{v.change_note || "—"}</td>
                          <td>{formatTime(v.changed_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}