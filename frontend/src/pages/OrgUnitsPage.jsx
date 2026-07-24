import { useEffect, useState } from "react";
import { AlertCircle, Plus, Power, PowerOff, Trash2 } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import {
  activateOrgUnit,
  createOrgUnit,
  deactivateOrgUnit,
  deleteOrgUnit,
  listOrgUnits,
} from "../api/orgUnits";

const UNIT_TYPES = [
  { value: "SO", label: "Sở" },
  { value: "PHONG", label: "Phòng" },
  { value: "XA", label: "Xã" },
];

const EMPTY_FORM = { code: "", name: "", unit_type: "SO", parent_id: "" };

export default function OrgUnitsPage() {
  const [units, setUnits] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  async function reload() {
    setLoading(true);
    try {
      const data = await listOrgUnits(false);
      setUnits(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await createOrgUnit({
        code: form.code,
        name: form.name,
        unit_type: form.unit_type,
        parent_id: form.parent_id ? Number(form.parent_id) : null,
      });
      setForm(EMPTY_FORM);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleActive(unit) {
    try {
      if (unit.is_active) {
        await deactivateOrgUnit(unit.id);
      } else {
        await activateOrgUnit(unit.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleDelete(unit) {
    try {
      await deleteOrgUnit(unit.id);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Cơ cấu tổ chức"
      subtitle="UC-01 — Quản lý danh mục đơn vị tổ chức dạng cây (Sở / Phòng / Xã)."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Thêm đơn vị mới</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="code">Mã đơn vị</label>
                <input
                  id="code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="name">Tên đơn vị</label>
                <input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="unit_type">Loại đơn vị</label>
                <select
                  id="unit_type"
                  value={form.unit_type}
                  onChange={(e) => setForm({ ...form, unit_type: e.target.value })}
                >
                  {UNIT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="parent_id">Đơn vị cha (ID, tuỳ chọn)</label>
                <input
                  id="parent_id"
                  value={form.parent_id}
                  onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
                />
              </div>
              <button type="submit" className="btn btn-primary">
                <Plus size={15} />
                Thêm đơn vị
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Danh sách đơn vị ({units.length})</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : units.length === 0 ? (
            <div className="empty-state">Chưa có đơn vị nào. Thêm đơn vị đầu tiên ở trên.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mã</th>
                  <th>Tên đơn vị</th>
                  <th>Loại</th>
                  <th>Đơn vị cha</th>
                  <th>Trạng thái</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.code}</td>
                    <td>{u.name}</td>
                    <td>{UNIT_TYPES.find((t) => t.value === u.unit_type)?.label || u.unit_type}</td>
                    <td>{u.parent_id ?? "—"}</td>
                    <td>
                      <span className={`badge ${u.is_active ? "badge-success" : "badge-neutral"}`}>
                        {u.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-btn"
                          title={u.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                          onClick={() => handleToggleActive(u)}
                        >
                          {u.is_active ? <PowerOff size={15} /> : <Power size={15} />}
                        </button>
                        <button
                          className="icon-btn"
                          title="Xoá"
                          onClick={() => handleDelete(u)}
                        >
                          <Trash2 size={15} />
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
