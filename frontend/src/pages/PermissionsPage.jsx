import { useEffect, useState } from "react";
import { AlertCircle, Save, ShieldCheck } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { listOrgUnits } from "../api/orgUnits";
import {
  assignRoleToUser,
  configureUserDomains,
  configureUserSensitivity,
  getPermissionContext,
} from "../api/permissions";
import { listRoles } from "../api/roles";
import { listUsers } from "../api/users";

const SENSITIVITY_LEVELS = [
  { value: "PUBLIC", label: "Công khai" },
  { value: "INTERNAL", label: "Nội bộ" },
  { value: "CONFIDENTIAL", label: "Mật" },
  { value: "SECRET", label: "Tối mật" },
];

export default function PermissionsPage() {
  const [users, setUsers] = useState([]);
  const [orgUnits, setOrgUnits] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [context, setContext] = useState(null);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(false);

  const [roleCode, setRoleCode] = useState("");
  const [domainsText, setDomainsText] = useState("");
  const [permittedUnitId, setPermittedUnitId] = useState("");
  const [sensitivityLevel, setSensitivityLevel] = useState("INTERNAL");

  async function reload() {
    setLoading(true);
    try {
      const [userList, orgUnitList, roleList] = await Promise.all([
        listUsers({ only_active: false }),
        listOrgUnits(false),
        listRoles(),
      ]);
      setUsers(userList);
      setOrgUnits(orgUnitList);
      setRoles(roleList);
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

  async function loadContext(userId) {
    if (!userId) {
      setContext(null);
      return;
    }
    setContextLoading(true);
    try {
      const ctx = await getPermissionContext(userId);
      setContext(ctx);
      setRoleCode(ctx.role_code);
      setDomainsText((ctx.permitted_domains || []).join(", "));
      setPermittedUnitId(ctx.permitted_unit_id ?? "");
      setSensitivityLevel(ctx.sensitivity_level);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setContextLoading(false);
    }
  }

  function handleSelectUser(e) {
    const id = e.target.value;
    setSelectedUserId(id);
    setInfo(null);
    loadContext(id);
  }

  function userName(id) {
    return users.find((u) => u.id === id)?.full_name || `#${id}`;
  }

  function orgUnitName(id) {
    return orgUnits.find((u) => u.id === id)?.name || `#${id}`;
  }

  async function handleAssignRole(e) {
    e.preventDefault();
    try {
      const ctx = await assignRoleToUser(selectedUserId, roleCode);
      setContext(ctx);
      setInfo("Đã cập nhật vai trò và lưu permission_context.");
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleConfigureDomains(e) {
    e.preventDefault();
    try {
      const domains = domainsText
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean);
      const unitId = permittedUnitId ? Number(permittedUnitId) : null;
      const ctx = await configureUserDomains(selectedUserId, domains, unitId);
      setContext(ctx);
      setInfo("Đã lưu miền dữ liệu và đơn vị được phép truy cập.");
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleConfigureSensitivity(e) {
    e.preventDefault();
    try {
      const ctx = await configureUserSensitivity(selectedUserId, sensitivityLevel);
      setContext(ctx);
      setInfo("Đã lưu mức nhạy cảm dữ liệu.");
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Quyền người dùng"
      subtitle="UC-04 — Xem và cấu hình quyền thực tế (permission_context) của từng người dùng."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && !error && (
        <div className="alert alert-success">
          <ShieldCheck size={16} />
          <span>{info}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Chọn người dùng</h2>
        </div>
        <div className="card-body">
          <div className="field">
            <label htmlFor="user_select">Người dùng</label>
            <select id="user_select" value={selectedUserId} onChange={handleSelectUser} disabled={loading}>
              <option value="">-- Chọn người dùng --</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.username})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {contextLoading && <div className="empty-state">Đang tải thông tin quyền...</div>}

      {!contextLoading && context && (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Thông tin quyền hiện tại</h2>
            </div>
            <div className="card-body">
              <table className="data-table">
                <tbody>
                  <tr>
                    <th style={{ width: 220 }}>Người dùng</th>
                    <td>{userName(context.user_id)}</td>
                  </tr>
                  <tr>
                    <th>Vai trò</th>
                    <td>
                      <span className="badge badge-success">{context.role_code}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>Miền dữ liệu được phép</th>
                    <td>
                      {(context.permitted_domains || []).length === 0
                        ? "—"
                        : context.permitted_domains.map((d) => (
                            <span key={d} className="badge badge-neutral" style={{ marginRight: 4 }}>
                              {d}
                            </span>
                          ))}
                    </td>
                  </tr>
                  <tr>
                    <th>Đơn vị được phép truy cập</th>
                    <td>
                      {context.permitted_unit_id ? orgUnitName(context.permitted_unit_id) : "—"}
                    </td>
                  </tr>
                  <tr>
                    <th>Mức nhạy cảm tối đa</th>
                    <td>
                      <span className="badge badge-neutral">
                        {SENSITIVITY_LEVELS.find((s) => s.value === context.sensitivity_level)
                          ?.label || context.sensitivity_level}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Phân quyền theo vai trò</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleAssignRole}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="role_code">Vai trò</label>
                    <select
                      id="role_code"
                      value={roleCode}
                      onChange={(e) => setRoleCode(e.target.value)}
                      required
                    >
                      <option value="" disabled>
                        Chọn vai trò
                      </option>
                      {roles.map((r) => (
                        <option key={r.code} value={r.code}>
                          {r.name} ({r.code})
                        </option>
                      ))}
                    </select>
                  </div>
                  <button type="submit" className="btn btn-primary">
                    <Save size={15} />
                    Lưu vai trò
                  </button>
                </div>
              </form>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Cấu hình miền dữ liệu + đơn vị</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleConfigureDomains}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="domains">Miền dữ liệu (phân cách bằng dấu phẩy)</label>
                    <input
                      id="domains"
                      placeholder="vd: TAI_SAN, NGAN_SACH, GIA"
                      value={domainsText}
                      onChange={(e) => setDomainsText(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="permitted_unit_id">Đơn vị được phép truy cập</label>
                    <select
                      id="permitted_unit_id"
                      value={permittedUnitId}
                      onChange={(e) => setPermittedUnitId(e.target.value)}
                    >
                      <option value="">-- Không giới hạn / bỏ trống --</option>
                      {orgUnits.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button type="submit" className="btn btn-primary">
                    <Save size={15} />
                    Lưu cấu hình
                  </button>
                </div>
              </form>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Cấu hình mức nhạy cảm</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleConfigureSensitivity}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="sensitivity">Mức nhạy cảm tối đa được xem</label>
                    <select
                      id="sensitivity"
                      value={sensitivityLevel}
                      onChange={(e) => setSensitivityLevel(e.target.value)}
                    >
                      {SENSITIVITY_LEVELS.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button type="submit" className="btn btn-primary">
                    <Save size={15} />
                    Lưu mức nhạy cảm
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}