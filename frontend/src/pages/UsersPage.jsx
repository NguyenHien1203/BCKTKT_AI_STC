import { useEffect, useState } from "react";
import { AlertCircle, Plus, Power, PowerOff, Trash2 } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { listOrgUnits } from "../api/orgUnits";
import {
  activateUser,
  createUser,
  deactivateUser,
  deleteUser,
  listUsers,
} from "../api/users";

const ROLES = [
  { value: "ADMIN", label: "Quản trị" },
  { value: "STAFF", label: "Cán bộ nghiệp vụ" },
  { value: "VIEWER", label: "Chỉ xem" },
];

const EMPTY_FORM = { username: "", full_name: "", email: "", org_unit_id: "", role: "STAFF" };

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [orgUnits, setOrgUnits] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  async function reload() {
    setLoading(true);
    try {
      const [userList, orgUnitList] = await Promise.all([
        listUsers({ only_active: false }),
        listOrgUnits(true),
      ]);
      setUsers(userList);
      setOrgUnits(orgUnitList);
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

  function orgUnitName(id) {
    return orgUnits.find((u) => u.id === id)?.name || `#${id}`;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await createUser({
        username: form.username,
        full_name: form.full_name,
        email: form.email,
        org_unit_id: Number(form.org_unit_id),
        role: form.role,
      });
      setForm(EMPTY_FORM);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleActive(user) {
    try {
      if (user.is_active) {
        await deactivateUser(user.id);
      } else {
        await activateUser(user.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleDelete(user) {
    try {
      await deleteUser(user.id);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Người dùng"
      subtitle="UC-02 — Quản lý tài khoản người dùng, gán đơn vị công tác và vai trò."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Thêm người dùng mới</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="username">Tên đăng nhập</label>
                <input
                  id="username"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="full_name">Họ và tên</label>
                <input
                  id="full_name"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="org_unit_id">Đơn vị công tác</label>
                <select
                  id="org_unit_id"
                  value={form.org_unit_id}
                  onChange={(e) => setForm({ ...form, org_unit_id: e.target.value })}
                  required
                >
                  <option value="" disabled>
                    Chọn đơn vị
                  </option>
                  {orgUnits.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="role">Vai trò</label>
                <select
                  id="role"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={orgUnits.length === 0}>
                <Plus size={15} />
                Thêm người dùng
              </button>
            </div>
            {orgUnits.length === 0 && !loading && (
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 10 }}>
                Chưa có đơn vị tổ chức đang hoạt động. Hãy tạo ở trang{" "}
                <strong>Cơ cấu tổ chức</strong> trước.
              </p>
            )}
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Danh sách người dùng ({users.length})</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : users.length === 0 ? (
            <div className="empty-state">Chưa có người dùng nào.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tên đăng nhập</th>
                  <th>Họ và tên</th>
                  <th>Email</th>
                  <th>Đơn vị</th>
                  <th>Vai trò</th>
                  <th>Trạng thái</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.username}</td>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>{orgUnitName(u.org_unit_id)}</td>
                    <td>{ROLES.find((r) => r.value === u.role)?.label || u.role}</td>
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
                        <button className="icon-btn" title="Xoá" onClick={() => handleDelete(u)}>
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
