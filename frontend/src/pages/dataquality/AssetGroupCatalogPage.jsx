import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  History,
  Layers,
  Percent,
  RefreshCw,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  createAssetGroup,
  declareAssetDepreciationRate,
  listAssetDepreciationRates,
  listAssetGroupVersions,
  listAssetGroups,
  updateAssetGroup,
} from "../../api/assetGroupCatalog.js";

const REGULATION_LABEL = {
  TT45: "TT 45/2018/TT-BTC",
  TT162: "TT 162/2014/TT-BTC",
};
const REGULATIONS = ["TT45", "TT162"];

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_CREATE_FORM = {
  code: "",
  name: "",
  regulation: "TT45",
  useful_life_years: "",
  effective_from: "",
  note: "",
};
const EMPTY_EDIT_FORM = {
  name: "",
  regulation: "TT45",
  useful_life_years: "",
  status: "ACTIVE",
  note: "",
};
const EMPTY_RATE_FORM = {
  depreciation_rate_percent: "",
  useful_life_years: "",
  effective_from: "",
  effective_to: "",
  declared_by: "",
  note: "",
};

export default function AssetGroupCatalogPage() {
  const [groups, setGroups] = useState([]);
  const [regulationFilter, setRegulationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [rates, setRates] = useState([]);
  const [activeTab, setActiveTab] = useState("create"); // create | edit | rate

  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);
  const [rateForm, setRateForm] = useState(EMPTY_RATE_FORM);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedGroup = groups.find((g) => g.id === selectedId) || null;

  async function loadGroups(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listAssetGroups({
        regulation: regulationFilter || null,
        status: statusFilter || null,
      });
      setGroups(data);
      if (!keepSelection || !data.some((g) => g.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(groupId) {
    if (!groupId) {
      setVersions([]);
      setRates([]);
      return;
    }
    try {
      const [v, r] = await Promise.all([
        listAssetGroupVersions(groupId),
        listAssetDepreciationRates(groupId),
      ]);
      setVersions(v);
      setRates(r);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadGroups(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regulationFilter, statusFilter]);

  useEffect(() => {
    loadDetail(selectedId);
    if (selectedGroup) {
      setEditForm({
        name: selectedGroup.name,
        regulation: selectedGroup.regulation,
        useful_life_years:
          selectedGroup.useful_life_years === null ? "" : String(selectedGroup.useful_life_years),
        status: selectedGroup.status,
        note: "",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await createAssetGroup({
        code: createForm.code.trim(),
        name: createForm.name.trim(),
        regulation: createForm.regulation,
        usefulLifeYears: createForm.useful_life_years
          ? Number(createForm.useful_life_years)
          : null,
        effectiveFrom: createForm.effective_from || null,
        note: createForm.note.trim() || null,
      });
      setInfo(`Đã thêm nhóm tài sản "${created.code}" (phiên bản ${created.version}).`);
      setError(null);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadGroups(false);
      setSelectedId(created.id);
      setActiveTab("edit");
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!selectedGroup) return;
    setSubmitting(true);
    try {
      const clearUseful =
        selectedGroup.useful_life_years !== null && editForm.useful_life_years === "";
      const updated = await updateAssetGroup(selectedGroup.id, {
        name: editForm.name.trim() || null,
        regulation: editForm.regulation || null,
        usefulLifeYears: editForm.useful_life_years ? Number(editForm.useful_life_years) : null,
        clearUsefulLifeYears: clearUseful,
        status: editForm.status || null,
        note: editForm.note.trim() || null,
      });
      setInfo(`Đã sửa nhóm tài sản "${updated.code}" -- phiên bản mới: ${updated.version}.`);
      setError(null);
      setEditForm((f) => ({ ...f, note: "" }));
      await loadGroups(true);
      await loadDetail(selectedGroup.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeclareRate(e) {
    e.preventDefault();
    if (!selectedGroup) return;
    setSubmitting(true);
    try {
      const rate = await declareAssetDepreciationRate(selectedGroup.id, {
        depreciationRatePercent: Number(rateForm.depreciation_rate_percent),
        usefulLifeYears: rateForm.useful_life_years ? Number(rateForm.useful_life_years) : null,
        effectiveFrom: rateForm.effective_from || null,
        effectiveTo: rateForm.effective_to || null,
        declaredBy: rateForm.declared_by.trim() || null,
        note: rateForm.note.trim() || null,
      });
      setInfo(
        `Đã khai báo tỉ lệ khấu hao ${rate.depreciation_rate_percent}%/năm cho nhóm "${selectedGroup.code}".`,
      );
      setError(null);
      setRateForm(EMPTY_RATE_FORM);
      await loadDetail(selectedGroup.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý danh mục nhóm tài sản"
      subtitle="UC-035 — Xem danh mục nhóm tài sản (TT 45/2018 sửa đổi TT 162/2014); thêm/sửa entry (hệ thống quản lý phiên bản); khai báo tỉ lệ khấu hao theo nhóm (hệ thống lưu)."
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

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 1: Xem danh mục ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 1 — Danh mục nhóm tài sản</h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadGroups(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="regulation-filter">Văn bản căn cứ</label>
                <select
                  id="regulation-filter"
                  value={regulationFilter}
                  onChange={(e) => setRegulationFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  {REGULATIONS.map((r) => (
                    <option key={r} value={r}>
                      {REGULATION_LABEL[r]}
                    </option>
                  ))}
                </select>
              </div>
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
            ) : groups.length === 0 ? (
              <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có nhóm tài sản nào.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Tên nhóm</th>
                    <th>Văn bản</th>
                    <th>Trạng thái</th>
                    <th>Phiên bản</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <tr
                      key={g.id}
                      onClick={() => setSelectedId(g.id)}
                      style={{
                        cursor: "pointer",
                        background:
                          selectedId === g.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
                      }}
                    >
                      <td>
                        <strong>{g.code}</strong>
                      </td>
                      <td>{g.name}</td>
                      <td>{REGULATION_LABEL[g.regulation] || g.regulation}</td>
                      <td>
                        <span className={`badge ${g.status === "ACTIVE" ? "badge-success" : "badge-danger"}`}>
                          {g.status === "ACTIVE" ? "Đang hoạt động" : "Đã đóng"}
                        </span>
                      </td>
                      <td>v{g.version}</td>
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
              {selectedGroup
                ? `Nhóm tài sản: ${selectedGroup.code} — ${selectedGroup.name}`
                : "Thêm nhóm tài sản mới"}
            </h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button
                className={`btn ${activeTab === "create" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab("create")}
              >
                Thêm mới
              </button>
              <button
                className={`btn ${activeTab === "edit" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab("edit")}
                disabled={!selectedGroup}
              >
                Sửa entry
              </button>
              <button
                className={`btn ${activeTab === "rate" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab("rate")}
                disabled={!selectedGroup}
              >
                <Percent size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Khai báo tỉ lệ khấu hao
              </button>
            </div>

            {activeTab === "create" && (
              <form onSubmit={handleCreate} className="form-grid">
                <div className="field">
                  <label htmlFor="c-code">Mã nhóm *</label>
                  <input
                    id="c-code"
                    required
                    value={createForm.code}
                    onChange={(e) => setCreateForm((f) => ({ ...f, code: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-name">Tên nhóm *</label>
                  <input
                    id="c-name"
                    required
                    value={createForm.name}
                    onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-regulation">Văn bản căn cứ *</label>
                  <select
                    id="c-regulation"
                    value={createForm.regulation}
                    onChange={(e) => setCreateForm((f) => ({ ...f, regulation: e.target.value }))}
                  >
                    {REGULATIONS.map((r) => (
                      <option key={r} value={r}>
                        {REGULATION_LABEL[r]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="c-life">Số năm sử dụng (tuỳ chọn)</label>
                  <input
                    id="c-life"
                    type="number"
                    min="1"
                    value={createForm.useful_life_years}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, useful_life_years: e.target.value }))
                    }
                  />
                </div>
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
                  <label htmlFor="c-note">Ghi chú</label>
                  <input
                    id="c-note"
                    value={createForm.note}
                    onChange={(e) => setCreateForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    <Layers size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    {submitting ? "Đang lưu..." : "Thêm nhóm tài sản"}
                  </button>
                </div>
              </form>
            )}

            {activeTab === "edit" && selectedGroup && (
              <form onSubmit={handleUpdate} className="form-grid">
                <div className="field">
                  <label htmlFor="e-name">Tên nhóm</label>
                  <input
                    id="e-name"
                    value={editForm.name}
                    onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="e-regulation">Văn bản căn cứ</label>
                  <select
                    id="e-regulation"
                    value={editForm.regulation}
                    onChange={(e) => setEditForm((f) => ({ ...f, regulation: e.target.value }))}
                  >
                    {REGULATIONS.map((r) => (
                      <option key={r} value={r}>
                        {REGULATION_LABEL[r]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="e-life">Số năm sử dụng (để trống để xoá)</label>
                  <input
                    id="e-life"
                    type="number"
                    min="1"
                    value={editForm.useful_life_years}
                    onChange={(e) =>
                      setEditForm((f) => ({ ...f, useful_life_years: e.target.value }))
                    }
                  />
                </div>
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
                  <label htmlFor="e-note">Ghi chú thay đổi</label>
                  <input
                    id="e-note"
                    value={editForm.note}
                    onChange={(e) => setEditForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? "Đang lưu..." : `Lưu (tạo phiên bản v${selectedGroup.version + 1})`}
                  </button>
                </div>
              </form>
            )}

            {activeTab === "rate" && selectedGroup && (
              <form onSubmit={handleDeclareRate} className="form-grid">
                <div className="field">
                  <label htmlFor="r-percent">Tỉ lệ khấu hao (%/năm) *</label>
                  <input
                    id="r-percent"
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="100"
                    required
                    value={rateForm.depreciation_rate_percent}
                    onChange={(e) =>
                      setRateForm((f) => ({ ...f, depreciation_rate_percent: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-life">Số năm sử dụng (tuỳ chọn)</label>
                  <input
                    id="r-life"
                    type="number"
                    min="1"
                    value={rateForm.useful_life_years}
                    onChange={(e) =>
                      setRateForm((f) => ({ ...f, useful_life_years: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-from">Hiệu lực từ</label>
                  <input
                    id="r-from"
                    type="date"
                    value={rateForm.effective_from}
                    onChange={(e) => setRateForm((f) => ({ ...f, effective_from: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-to">Hiệu lực đến (tuỳ chọn)</label>
                  <input
                    id="r-to"
                    type="date"
                    value={rateForm.effective_to}
                    onChange={(e) => setRateForm((f) => ({ ...f, effective_to: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-by">Người khai báo</label>
                  <input
                    id="r-by"
                    value={rateForm.declared_by}
                    onChange={(e) => setRateForm((f) => ({ ...f, declared_by: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="r-note">Ghi chú</label>
                  <input
                    id="r-note"
                    value={rateForm.note}
                    onChange={(e) => setRateForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    <Percent size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    {submitting ? "Đang lưu..." : "Khai báo tỉ lệ khấu hao"}
                  </button>
                </div>
              </form>
            )}

            {selectedGroup && (
              <>
                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <Percent size={16} /> Lịch sử tỉ lệ khấu hao đã khai báo
                </h3>
                {rates.length === 0 ? (
                  <p style={{ color: "var(--color-text-secondary, #888)" }}>
                    Chưa khai báo tỉ lệ khấu hao nào cho nhóm này.
                  </p>
                ) : (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Tỉ lệ (%/năm)</th>
                        <th>Số năm sử dụng</th>
                        <th>Hiệu lực từ</th>
                        <th>Hiệu lực đến</th>
                        <th>Người khai báo</th>
                        <th>Thời điểm lưu</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rates.map((r) => (
                        <tr key={r.id}>
                          <td>{r.depreciation_rate_percent}</td>
                          <td>{r.useful_life_years ?? "—"}</td>
                          <td>{r.effective_from || "—"}</td>
                          <td>{r.effective_to || "—"}</td>
                          <td>{r.declared_by || "—"}</td>
                          <td>{formatTime(r.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <History size={16} /> Lịch sử phiên bản
                </h3>
                {versions.length === 0 ? (
                  <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có lịch sử.</p>
                ) : (
                  <table className="table">
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