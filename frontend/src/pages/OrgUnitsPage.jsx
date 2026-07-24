import { useEffect, useState } from "react";
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

export default function OrgUnitsPage() {
  const [units, setUnits] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", unit_type: "SO", parent_id: "" });

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
      setForm({ code: "", name: "", unit_type: "SO", parent_id: "" });
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
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>UC-01: Quản lý cơ cấu tổ chức</h1>

      {error && <div style={{ color: "red", marginBottom: 12 }}>Lỗi: {error}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: 24, display: "flex", gap: 8 }}>
        <input
          placeholder="Mã đơn vị"
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
          required
        />
        <input
          placeholder="Tên đơn vị"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <select
          value={form.unit_type}
          onChange={(e) => setForm({ ...form, unit_type: e.target.value })}
        >
          {UNIT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          placeholder="ID đơn vị cha (tuỳ chọn)"
          value={form.parent_id}
          onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
        />
        <button type="submit">Thêm đơn vị</button>
      </form>

      {loading ? (
        <p>Đang tải...</p>
      ) : (
        <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Mã</th>
              <th>Tên</th>
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
                <td>{u.unit_type}</td>
                <td>{u.parent_id ?? "-"}</td>
                <td>{u.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}</td>
                <td>
                  <button onClick={() => handleToggleActive(u)}>
                    {u.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                  </button>
                  <button onClick={() => handleDelete(u)} style={{ marginLeft: 8 }}>
                    Xoá
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
