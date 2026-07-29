import { useEffect, useState } from "react";
import { AlertCircle, Pencil, Plus, Power, PowerOff, X } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  activateDataSource,
  deactivateDataSource,
  listDataSources,
  registerDataSource,
  updateDataSource,
} from "../../api/dataSources.js";

const SOURCE_SYSTEMS = [
  { value: "TABMIS", label: "TABMIS" },
  { value: "QLVBDH", label: "QLVBĐH" },
  { value: "MISA", label: "MISA" },
  { value: "QL_GIA", label: "QL Giá" },
  { value: "PMSTT", label: "PMSTT" },
];

const SENSITIVITY_LEVELS = [
  { value: "PUBLIC", label: "Công khai" },
  { value: "INTERNAL", label: "Nội bộ" },
  { value: "CONFIDENTIAL", label: "Mật" },
  { value: "SECRET", label: "Tối mật" },
];

const SENSITIVITY_BADGE = {
  PUBLIC: "badge-success",
  INTERNAL: "badge-neutral",
  CONFIDENTIAL: "badge-danger",
  SECRET: "badge-danger",
};

const EMPTY_FORM = {
  code: "",
  name: "",
  source_system: SOURCE_SYSTEMS[0].value,
  provider: "",
  owner: "",
  sensitivity_level: "INTERNAL",
};

function sourceSystemLabel(value) {
  return SOURCE_SYSTEMS.find((s) => s.value === value)?.label || value;
}

function sensitivityLabel(value) {
  return SENSITIVITY_LEVELS.find((s) => s.value === value)?.label || value;
}

export default function DataSourcesPage() {
  const [sources, setSources] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [onlyActive, setOnlyActive] = useState(false);
  const [filterSystem, setFilterSystem] = useState("");

  async function reload() {
    setLoading(true);
    try {
      const data = await listDataSources({
        onlyActive,
        sourceSystem: filterSystem || null,
      });
      setSources(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyActive, filterSystem]);

  function startEdit(source) {
    setEditingId(source.id);
    setForm({
      code: source.code,
      name: source.name,
      source_system: source.source_system,
      provider: source.provider,
      owner: source.owner,
      sensitivity_level: source.sensitivity_level,
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      if (editingId) {
        await updateDataSource(editingId, {
          provider: form.provider,
          owner: form.owner,
          sensitivity_level: form.sensitivity_level,
        });
      } else {
        await registerDataSource({
          code: form.code,
          name: form.name,
          source_system: form.source_system,
          provider: form.provider,
          owner: form.owner,
          sensitivity_level: form.sensitivity_level,
        });
      }
      cancelEdit();
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleActive(source) {
    try {
      if (source.is_active) {
        await deactivateDataSource(source.id);
      } else {
        await activateDataSource(source.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Nguồn dữ liệu"
      subtitle="UC-015 — Đăng ký và quản lý nguồn dữ liệu (TABMIS, QLVBĐH, MISA, QL Giá, PMSTT)."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>{editingId ? "Sửa thông tin nguồn" : "Đăng ký nguồn mới"}</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="code">Mã nguồn</label>
                <input
                  id="code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  required
                  disabled={!!editingId}
                />
              </div>
              <div className="field">
                <label htmlFor="name">Tên nguồn</label>
                <input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  disabled={!!editingId}
                />
              </div>
              <div className="field">
                <label htmlFor="source_system">Hệ thống nguồn</label>
                <select
                  id="source_system"
                  value={form.source_system}
                  onChange={(e) => setForm({ ...form, source_system: e.target.value })}
                  disabled={!!editingId}
                >
                  {SOURCE_SYSTEMS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="provider">Nhà cung cấp</label>
                <input
                  id="provider"
                  value={form.provider}
                  onChange={(e) => setForm({ ...form, provider: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="owner">Chủ sở hữu</label>
                <input
                  id="owner"
                  value={form.owner}
                  onChange={(e) => setForm({ ...form, owner: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="sensitivity_level">Mức nhạy cảm</label>
                <select
                  id="sensitivity_level"
                  value={form.sensitivity_level}
                  onChange={(e) => setForm({ ...form, sensitivity_level: e.target.value })}
                >
                  {SENSITIVITY_LEVELS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  {editingId ? <Pencil size={15} /> : <Plus size={15} />}
                  {editingId ? "Lưu thay đổi" : "Đăng ký nguồn"}
                </button>
                {editingId && (
                  <button type="button" className="btn" onClick={cancelEdit}>
                    <X size={15} />
                    Huỷ
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Danh sách nguồn ({sources.length})</h2>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <select
              value={filterSystem}
              onChange={(e) => setFilterSystem(e.target.value)}
              style={{ width: "auto" }}
            >
              <option value="">Tất cả hệ thống nguồn</option>
              {SOURCE_SYSTEMS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={onlyActive}
                onChange={(e) => setOnlyActive(e.target.checked)}
              />
              Chỉ hiện đang hoạt động
            </label>
          </div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : sources.length === 0 ? (
            <div className="empty-state">Chưa có nguồn nào. Đăng ký nguồn đầu tiên ở trên.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mã</th>
                  <th>Tên nguồn</th>
                  <th>Hệ thống nguồn</th>
                  <th>Nhà cung cấp</th>
                  <th>Chủ sở hữu</th>
                  <th>Mức nhạy cảm</th>
                  <th>Trạng thái</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{s.code}</td>
                    <td>{s.name}</td>
                    <td>{sourceSystemLabel(s.source_system)}</td>
                    <td>{s.provider || "—"}</td>
                    <td>{s.owner || "—"}</td>
                    <td>
                      <span className={`badge ${SENSITIVITY_BADGE[s.sensitivity_level] || "badge-neutral"}`}>
                        {sensitivityLabel(s.sensitivity_level)}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${s.is_active ? "badge-success" : "badge-neutral"}`}>
                        {s.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-btn" title="Sửa" onClick={() => startEdit(s)}>
                          <Pencil size={15} />
                        </button>
                        <button
                          className="icon-btn"
                          title={s.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                          onClick={() => handleToggleActive(s)}
                        >
                          {s.is_active ? <PowerOff size={15} /> : <Power size={15} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  );
}