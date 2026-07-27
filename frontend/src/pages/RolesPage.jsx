import { useEffect, useState } from "react";
import { AlertCircle, Pencil, Plus, Trash2, X } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { createRole, deleteRole, listRoles, updateRole } from "../api/roles.js";

const EMPTY_FORM = { code: "", name: "", description: "", permissions: "" };

function toPermissionsArray(text) {
  return text
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

export default function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);

  async function reload() {
    setLoading(true);
    try {
      const data = await listRoles();
      setRoles(data);
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

  function startEdit(role) {
    setEditingId(role.id);
    setForm({
      code: role.code,
      name: role.name,
      description: role.description || "",
      permissions: (role.permissions || []).join(", "),
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
        await updateRole(editingId, {
          name: form.name,
          description: form.description,
          permissions: toPermissionsArray(form.permissions),
        });
      } else {
        await createRole({
          code: form.code,
          name: form.name,
          description: form.description,
          permissions: toPermissionsArray(form.permissions),
        });
      }
      cancelEdit();
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleDelete(role) {
    try {
      await deleteRole(role.id);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Vai trò người dùng"
      subtitle="UC-05 — Quản lý danh mục vai trò và bộ quyền gán cho từng vai trò."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>{editingId ? "Sửa vai trò" : "Thêm vai trò mới"}</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="code">Mã vai trò</label>
                <input
                  id="code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  required
                  disabled={!!editingId}
                />
              </div>
              <div className="field">
                <label htmlFor="name">Tên vai trò</label>
                <input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="description">Mô tả</label>
                <input
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="permissions">Bộ quyền (phân cách bằng dấu phẩy)</label>
                <input
                  id="permissions"
                  placeholder="vd: REPORT_VIEW, BUDGET_VIEW"
                  value={form.permissions}
                  onChange={(e) => setForm({ ...form, permissions: e.target.value })}
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  {editingId ? <Pencil size={15} /> : <Plus size={15} />}
                  {editingId ? "Lưu thay đổi" : "Thêm vai trò"}
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
        <div className="card-header">
          <h2>Danh sách vai trò ({roles.length})</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : roles.length === 0 ? (
            <div className="empty-state">Chưa có vai trò nào. Thêm vai trò đầu tiên ở trên.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mã</th>
                  <th>Tên vai trò</th>
                  <th>Mô tả</th>
                  <th>Bộ quyền</th>
                  <th>Phiên bản</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.code}</td>
                    <td>{r.name}</td>
                    <td>{r.description || "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {(r.permissions || []).length === 0
                          ? "—"
                          : r.permissions.map((p) => (
                              <span key={p} className="badge badge-neutral">
                                {p}
                              </span>
                            ))}
                      </div>
                    </td>
                    <td>v{r.version}</td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-btn" title="Sửa" onClick={() => startEdit(r)}>
                          <Pencil size={15} />
                        </button>
                        <button className="icon-btn" title="Xoá" onClick={() => handleDelete(r)}>
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