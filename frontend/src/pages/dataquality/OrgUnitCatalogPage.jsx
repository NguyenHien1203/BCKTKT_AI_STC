import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  GitMerge,
  History,
  Network,
  Plus,
  RefreshCw,
  Scissors,
  XCircle,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  closeOrgUnit,
  createOrgUnit,
  getOrgUnitTree,
  listOrgUnitVersions,
  mergeOrgUnits,
  splitOrgUnit,
  updateOrgUnit,
} from "../../api/orgUnitCatalog.js";

const UNIT_TYPE_LABEL = { SO: "Sở", PHONG: "Phòng", XA: "Xã" };
const UNIT_TYPES = ["SO", "PHONG", "XA"];

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function flattenTree(nodes, acc = []) {
  for (const n of nodes) {
    acc.push(n.unit);
    flattenTree(n.children, acc);
  }
  return acc;
}

const EMPTY_CREATE_FORM = { code: "", name: "", unit_type: "SO", parent_id: "", effective_from: "", note: "" };
const EMPTY_EDIT_FORM = { name: "", unit_type: "", parent_id: "", note: "" };
const EMPTY_CLOSE_FORM = { effective_to: "", note: "" };
const EMPTY_SPLIT_FORM = {
  effective_from: "",
  note: "",
  new_units: [
    { code: "", name: "", unit_type: "" },
    { code: "", name: "", unit_type: "" },
  ],
};
const EMPTY_MERGE_TARGET = { code: "", name: "", unit_type: "SO", parent_id: "" };

function TreeNode({ node, depth, expanded, onToggle, selectedId, onSelect, mergeSelection, onToggleMerge }) {
  const unit = node.unit;
  const isExpanded = expanded.has(unit.id);
  const hasChildren = node.children.length > 0;

  return (
    <>
      <div
        className={`org-tree-row ${selectedId === unit.id ? "org-tree-row-active" : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 8px",
          paddingLeft: 8 + depth * 20,
          borderBottom: "1px solid var(--color-border, #eee)",
          cursor: "pointer",
          background: selectedId === unit.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
        }}
        onClick={() => onSelect(unit.id)}
      >
        <span
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(unit.id);
          }}
          style={{ width: 16, display: "inline-flex", justifyContent: "center", color: "var(--color-text-secondary, #888)" }}
        >
          {hasChildren ? isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} /> : null}
        </span>
        <input
          type="checkbox"
          checked={mergeSelection.has(unit.id)}
          disabled={unit.status !== "ACTIVE"}
          onClick={(e) => e.stopPropagation()}
          onChange={() => onToggleMerge(unit.id)}
          title="Chọn để sáp nhập"
        />
        <span className="badge badge-neutral">{UNIT_TYPE_LABEL[unit.unit_type] || unit.unit_type}</span>
        <strong>{unit.code}</strong>
        <span>{unit.name}</span>
        <span className={`badge ${unit.status === "ACTIVE" ? "badge-success" : "badge-danger"}`}>
          {unit.status === "ACTIVE" ? "Đang hoạt động" : "Đã đóng"}
        </span>
        <span style={{ color: "var(--color-text-secondary, #888)", fontSize: 12 }}>v{unit.version}</span>
        {unit.lifecycle_action && (
          <span className="badge badge-warning">{unit.lifecycle_action}</span>
        )}
      </div>
      {hasChildren && isExpanded
        ? node.children.map((c) => (
            <TreeNode
              key={c.unit.id}
              node={c}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
              mergeSelection={mergeSelection}
              onToggleMerge={onToggleMerge}
            />
          ))
        : null}
    </>
  );
}

export default function OrgUnitCatalogPage() {
  const [tree, setTree] = useState([]);
  const [includeClosed, setIncludeClosed] = useState(true);
  const [expanded, setExpanded] = useState(new Set());
  const [selectedId, setSelectedId] = useState(null);
  const [mergeSelection, setMergeSelection] = useState(new Set());
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const [activePanel, setActivePanel] = useState("create"); // create | edit | close | split | merge
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);
  const [closeForm, setCloseForm] = useState(EMPTY_CLOSE_FORM);
  const [splitForm, setSplitForm] = useState(EMPTY_SPLIT_FORM);
  const [mergeTarget, setMergeTarget] = useState(EMPTY_MERGE_TARGET);
  const [mergeEffectiveFrom, setMergeEffectiveFrom] = useState("");
  const [mergeNote, setMergeNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const flatUnits = useMemo(() => flattenTree(tree), [tree]);
  const selectedUnit = useMemo(
    () => flatUnits.find((u) => u.id === selectedId) || null,
    [flatUnits, selectedId],
  );

  async function loadTree() {
    setLoading(true);
    try {
      const data = await getOrgUnitTree({ includeClosed });
      setTree(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(unitId) {
    try {
      setVersions(await listOrgUnitVersions(unitId));
    } catch (e) {
      setVersions([]);
    }
  }

  useEffect(() => {
    loadTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeClosed]);

  useEffect(() => {
    if (selectedUnit) {
      setEditForm({
        name: selectedUnit.name,
        unit_type: selectedUnit.unit_type,
        parent_id: selectedUnit.parent_id || "",
        note: "",
      });
      setCloseForm(EMPTY_CLOSE_FORM);
      setSplitForm(EMPTY_SPLIT_FORM);
      loadVersions(selectedUnit.id);
    } else {
      setVersions([]);
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

  function toggleMergeSelection(id) {
    setMergeSelection((prev) => {
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

  // ---------- Bước 2: Thêm đơn vị mới ----------
  async function handleCreate() {
    setSubmitting(true);
    try {
      const unit = await createOrgUnit({
        code: createForm.code.trim(),
        name: createForm.name.trim(),
        unitType: createForm.unit_type,
        parentId: createForm.parent_id ? Number(createForm.parent_id) : null,
        effectiveFrom: createForm.effective_from || null,
        note: createForm.note || null,
      });
      reportSuccess(`Đã thêm đơn vị "${unit.code}" (phiên bản 1).`);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadTree();
      setSelectedId(unit.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 3: Sửa thông tin đơn vị ----------
  async function handleUpdate() {
    if (!selectedUnit) return;
    setSubmitting(true);
    try {
      const updated = await updateOrgUnit(selectedUnit.id, {
        name: editForm.name,
        unitType: editForm.unit_type,
        parentId: editForm.parent_id ? Number(editForm.parent_id) : undefined,
        clearParent: editForm.parent_id === "",
        note: editForm.note || null,
      });
      reportSuccess(`Đã lưu đơn vị "${updated.code}" (phiên bản ${updated.version}).`);
      await loadTree();
      await loadVersions(updated.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 4: Đóng đơn vị ----------
  async function handleClose() {
    if (!selectedUnit) return;
    setSubmitting(true);
    try {
      const closed = await closeOrgUnit(selectedUnit.id, {
        effectiveTo: closeForm.effective_to,
        note: closeForm.note || null,
      });
      reportSuccess(`Đã đóng đơn vị "${closed.code}" hiệu lực đến ${closed.effective_to}.`);
      await loadTree();
      await loadVersions(closed.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 4: Tách đơn vị ----------
  function updateSplitChild(index, field, value) {
    setSplitForm((prev) => {
      const newUnits = [...prev.new_units];
      newUnits[index] = { ...newUnits[index], [field]: value };
      return { ...prev, new_units: newUnits };
    });
  }

  function addSplitChild() {
    setSplitForm((prev) => ({
      ...prev,
      new_units: [...prev.new_units, { code: "", name: "", unit_type: "" }],
    }));
  }

  function removeSplitChild(index) {
    setSplitForm((prev) => ({
      ...prev,
      new_units: prev.new_units.filter((_, i) => i !== index),
    }));
  }

  async function handleSplit() {
    if (!selectedUnit) return;
    setSubmitting(true);
    try {
      const payloadUnits = splitForm.new_units
        .filter((u) => u.code.trim() && u.name.trim())
        .map((u) => ({
          code: u.code.trim(),
          name: u.name.trim(),
          unit_type: u.unit_type || undefined,
        }));
      const result = await splitOrgUnit(selectedUnit.id, {
        effectiveFrom: splitForm.effective_from,
        newUnits: payloadUnits,
        note: splitForm.note || null,
      });
      reportSuccess(
        `Đã tách "${result.source.code}" thành ${result.created_units.length} đơn vị mới, hiệu lực từ ${splitForm.effective_from}.`,
      );
      setSplitForm(EMPTY_SPLIT_FORM);
      await loadTree();
      setSelectedId(result.source.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Bước 4: Sáp nhập đơn vị ----------
  async function handleMerge() {
    setSubmitting(true);
    try {
      const sourceUnitIds = Array.from(mergeSelection);
      const result = await mergeOrgUnits({
        sourceUnitIds,
        target: {
          code: mergeTarget.code.trim(),
          name: mergeTarget.name.trim(),
          unit_type: mergeTarget.unit_type || undefined,
          parent_id: mergeTarget.parent_id ? Number(mergeTarget.parent_id) : undefined,
        },
        effectiveFrom: mergeEffectiveFrom,
        note: mergeNote || null,
      });
      reportSuccess(
        `Đã sáp nhập ${result.source_units.length} đơn vị thành "${result.merged_unit.code}", hiệu lực từ ${mergeEffectiveFrom}.`,
      );
      setMergeSelection(new Set());
      setMergeTarget(EMPTY_MERGE_TARGET);
      setMergeEffectiveFrom("");
      setMergeNote("");
      await loadTree();
      setSelectedId(result.merged_unit.id);
    } catch (e) {
      reportError(e);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý danh mục đơn vị"
      subtitle="UC-033 — Xem danh mục đơn vị dạng cây phân cấp; thêm đơn vị mới (kiểm tra trùng mã, lưu phiên bản); sửa thông tin đơn vị; đóng/tách/sáp nhập đơn vị (lưu effective_from/effective_to)."
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
        {/* ---------- Bước 1: Xem danh mục đơn vị (cây phân cấp) ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              <Network size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Bước 1 — Danh mục đơn vị (cây phân cấp)
            </h2>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={includeClosed}
                  onChange={(e) => setIncludeClosed(e.target.checked)}
                />
                Gồm đơn vị đã đóng
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
              <div className="empty-state">Danh mục đơn vị chưa có dữ liệu.</div>
            ) : (
              <div style={{ maxHeight: 560, overflowY: "auto" }}>
                {tree.map((n) => (
                  <TreeNode
                    key={n.unit.id}
                    node={n}
                    depth={0}
                    expanded={expanded}
                    onToggle={toggleExpand}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                    mergeSelection={mergeSelection}
                    onToggleMerge={toggleMergeSelection}
                  />
                ))}
              </div>
            )}
          </div>
          {mergeSelection.size > 0 && (
            <div className="card-body" style={{ borderTop: "1px solid var(--color-border, #eee)" }}>
              <span>Đã chọn {mergeSelection.size} đơn vị để sáp nhập.</span>{" "}
              <button className="btn btn-secondary" onClick={() => setActivePanel("merge")}>
                <GitMerge size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Sáp nhập đã chọn
              </button>{" "}
              <button className="btn btn-secondary" onClick={() => setMergeSelection(new Set())}>
                Bỏ chọn
              </button>
            </div>
          )}
        </div>

        {/* ---------- Panel thao tác ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Thao tác</h2>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <button
                className={`btn ${activePanel === "create" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("create")}
              >
                <Plus size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Thêm mới
              </button>
              <button
                className={`btn ${activePanel === "edit" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("edit")}
                disabled={!selectedUnit}
              >
                Sửa
              </button>
              <button
                className={`btn ${activePanel === "close" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("close")}
                disabled={!selectedUnit || selectedUnit.status !== "ACTIVE"}
              >
                <XCircle size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Đóng
              </button>
              <button
                className={`btn ${activePanel === "split" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("split")}
                disabled={!selectedUnit || selectedUnit.status !== "ACTIVE"}
              >
                <Scissors size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Tách
              </button>
            </div>
          </div>
          <div className="card-body">
            {selectedUnit && activePanel !== "create" && activePanel !== "merge" && (
              <p style={{ marginTop: 0, color: "var(--color-text-secondary, #888)" }}>
                Đang thao tác trên: <strong>{selectedUnit.code}</strong> — {selectedUnit.name}
              </p>
            )}

            {activePanel === "create" && (
              <div className="form-grid">
                <div className="field">
                  <label>Mã đơn vị</label>
                  <input
                    type="text"
                    value={createForm.code}
                    onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Tên đơn vị</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Loại đơn vị</label>
                  <select
                    value={createForm.unit_type}
                    onChange={(e) => setCreateForm({ ...createForm, unit_type: e.target.value })}
                  >
                    {UNIT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {UNIT_TYPE_LABEL[t]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Đơn vị cha (tuỳ chọn)</label>
                  <select
                    value={createForm.parent_id}
                    onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value })}
                  >
                    <option value="">-- Không có (gốc cây) --</option>
                    {flatUnits.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.code} — {u.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Hiệu lực từ (tuỳ chọn)</label>
                  <input
                    type="date"
                    value={createForm.effective_from}
                    onChange={(e) => setCreateForm({ ...createForm, effective_from: e.target.value })}
                  />
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
                  {submitting ? "Đang lưu..." : "Thêm đơn vị (bước 2)"}
                </button>
              </div>
            )}

            {activePanel === "edit" && selectedUnit && (
              <div className="form-grid">
                <div className="field">
                  <label>Tên đơn vị</label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Loại đơn vị</label>
                  <select
                    value={editForm.unit_type}
                    onChange={(e) => setEditForm({ ...editForm, unit_type: e.target.value })}
                  >
                    {UNIT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {UNIT_TYPE_LABEL[t]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Đơn vị cha</label>
                  <select
                    value={editForm.parent_id}
                    onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value })}
                  >
                    <option value="">-- Không có (gốc cây) --</option>
                    {flatUnits
                      .filter((u) => u.id !== selectedUnit.id)
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.code} — {u.name}
                        </option>
                      ))}
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
                  disabled={submitting || selectedUnit.status !== "ACTIVE"}
                  onClick={handleUpdate}
                >
                  {submitting ? "Đang lưu..." : "Lưu thay đổi (bước 3)"}
                </button>
                {selectedUnit.status !== "ACTIVE" && (
                  <span style={{ color: "var(--color-danger)", fontSize: 13 }}>
                    Đơn vị đã đóng, không thể sửa thông tin.
                  </span>
                )}
              </div>
            )}

            {activePanel === "close" && selectedUnit && (
              <div className="form-grid">
                <div className="field">
                  <label>Hiệu lực đến (effective_to)</label>
                  <input
                    type="date"
                    value={closeForm.effective_to}
                    onChange={(e) => setCloseForm({ ...closeForm, effective_to: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Ghi chú / lý do đóng</label>
                  <input
                    type="text"
                    value={closeForm.note}
                    onChange={(e) => setCloseForm({ ...closeForm, note: e.target.value })}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  disabled={submitting || !closeForm.effective_to}
                  onClick={handleClose}
                >
                  {submitting ? "Đang lưu..." : "Đóng đơn vị (bước 4)"}
                </button>
              </div>
            )}

            {activePanel === "split" && selectedUnit && (
              <div>
                <div className="form-grid">
                  <div className="field">
                    <label>Hiệu lực từ (effective_from)</label>
                    <input
                      type="date"
                      value={splitForm.effective_from}
                      onChange={(e) => setSplitForm({ ...splitForm, effective_from: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Ghi chú / căn cứ tách</label>
                    <input
                      type="text"
                      value={splitForm.note}
                      onChange={(e) => setSplitForm({ ...splitForm, note: e.target.value })}
                    />
                  </div>
                </div>
                <h3 style={{ fontSize: 14, marginTop: 16 }}>Các đơn vị mới sau khi tách</h3>
                {splitForm.new_units.map((u, idx) => (
                  <div
                    key={idx}
                    style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}
                  >
                    <input
                      type="text"
                      placeholder="Mã đơn vị mới"
                      value={u.code}
                      onChange={(e) => updateSplitChild(idx, "code", e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="Tên đơn vị mới"
                      value={u.name}
                      onChange={(e) => updateSplitChild(idx, "name", e.target.value)}
                      style={{ flex: 2 }}
                    />
                    <select
                      value={u.unit_type}
                      onChange={(e) => updateSplitChild(idx, "unit_type", e.target.value)}
                    >
                      <option value="">(giữ loại gốc)</option>
                      {UNIT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {UNIT_TYPE_LABEL[t]}
                        </option>
                      ))}
                    </select>
                    {splitForm.new_units.length > 2 && (
                      <button className="btn-danger-ghost" onClick={() => removeSplitChild(idx)}>
                        Xoá
                      </button>
                    )}
                  </div>
                ))}
                <button className="btn btn-secondary" onClick={addSplitChild} style={{ marginBottom: 12 }}>
                  + Thêm đơn vị mới
                </button>
                <div>
                  <button
                    className="btn btn-primary"
                    disabled={submitting || !splitForm.effective_from}
                    onClick={handleSplit}
                  >
                    {submitting ? "Đang lưu..." : "Tách đơn vị (bước 4)"}
                  </button>
                </div>
              </div>
            )}

            {activePanel === "merge" && (
              <div className="form-grid">
                <p style={{ gridColumn: "1 / -1" }}>
                  Sáp nhập {mergeSelection.size} đơn vị đã chọn ở cây bên trái thành 1 đơn vị mới.
                </p>
                <div className="field">
                  <label>Mã đơn vị mới</label>
                  <input
                    type="text"
                    value={mergeTarget.code}
                    onChange={(e) => setMergeTarget({ ...mergeTarget, code: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Tên đơn vị mới</label>
                  <input
                    type="text"
                    value={mergeTarget.name}
                    onChange={(e) => setMergeTarget({ ...mergeTarget, name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Loại đơn vị</label>
                  <select
                    value={mergeTarget.unit_type}
                    onChange={(e) => setMergeTarget({ ...mergeTarget, unit_type: e.target.value })}
                  >
                    {UNIT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {UNIT_TYPE_LABEL[t]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Hiệu lực từ (effective_from)</label>
                  <input
                    type="date"
                    value={mergeEffectiveFrom}
                    onChange={(e) => setMergeEffectiveFrom(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Ghi chú / căn cứ sáp nhập</label>
                  <input type="text" value={mergeNote} onChange={(e) => setMergeNote(e.target.value)} />
                </div>
                <button
                  className="btn btn-primary"
                  disabled={
                    submitting ||
                    mergeSelection.size < 2 ||
                    !mergeTarget.code.trim() ||
                    !mergeTarget.name.trim() ||
                    !mergeEffectiveFrom
                  }
                  onClick={handleMerge}
                >
                  {submitting ? "Đang lưu..." : "Sáp nhập đơn vị (bước 4)"}
                </button>
              </div>
            )}

            {selectedUnit && (
              <div style={{ marginTop: 20 }}>
                <h3 style={{ fontSize: 14 }}>
                  <History size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                  Lịch sử phiên bản
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
                        <th>Hiệu lực từ</th>
                        <th>Hiệu lực đến</th>
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
                          <td>{v.effective_from || "—"}</td>
                          <td>{v.effective_to || "—"}</td>
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