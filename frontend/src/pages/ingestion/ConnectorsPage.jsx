import { useEffect, useState } from "react";
import { AlertCircle, Plus, Power, PowerOff, RefreshCw, X } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  activateConnector,
  deactivateConnector,
  listConnectors,
  registerConnector,
  updateConnectorVersion,
} from "../../api/connectors.js";

const CONNECTOR_TYPES = [
  { value: "FILE", label: "Tệp" },
  { value: "REST_API", label: "REST API" },
  { value: "JDBC", label: "JDBC" },
  { value: "SOAP", label: "SOAP" },
];

const INTERFACE_BADGE = {
  PASSED: "badge-success",
  FAILED: "badge-danger",
};

const EMPTY_FORM = {
  code: "",
  name: "",
  connector_type: CONNECTOR_TYPES[0].value,
  version: "",
  entry_point: "",
  description: "",
};

function connectorTypeLabel(value) {
  return CONNECTOR_TYPES.find((t) => t.value === value)?.label || value;
}

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [onlyActive, setOnlyActive] = useState(false);
  const [filterType, setFilterType] = useState("");
  const [versionDrafts, setVersionDrafts] = useState({});

  async function reload() {
    setLoading(true);
    try {
      const data = await listConnectors({
        onlyActive,
        connectorType: filterType || null,
      });
      setConnectors(data);
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
  }, [onlyActive, filterType]);

  function resetForm() {
    setForm(EMPTY_FORM);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await registerConnector(form);
      resetForm();
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleActive(connector) {
    try {
      if (connector.is_active) {
        await deactivateConnector(connector.id);
      } else {
        await activateConnector(connector.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleUpdateVersion(connector) {
    const newVersion = (versionDrafts[connector.id] || "").trim();
    if (!newVersion) return;
    try {
      await updateConnectorVersion(connector.id, newVersion);
      setVersionDrafts((prev) => ({ ...prev, [connector.id]: "" }));
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Thư viện bộ kết nối"
      subtitle="UC-016 — Xem danh sách, đăng ký (plugin) và cập nhật phiên bản bộ kết nối (tệp/REST API/JDBC/SOAP)."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Đăng ký bộ kết nối mới (plugin)</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="code">Mã bộ kết nối</label>
                <input
                  id="code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="name">Tên bộ kết nối</label>
                <input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="connector_type">Loại bộ kết nối</label>
                <select
                  id="connector_type"
                  value={form.connector_type}
                  onChange={(e) => setForm({ ...form, connector_type: e.target.value })}
                >
                  {CONNECTOR_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="version">Phiên bản</label>
                <input
                  id="version"
                  placeholder="vd: 1.0.0"
                  value={form.version}
                  onChange={(e) => setForm({ ...form, version: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="entry_point">Mô-đun plugin (entry point)</label>
                <input
                  id="entry_point"
                  placeholder="vd: connectors.rest_api:RestApiConnector"
                  value={form.entry_point}
                  onChange={(e) => setForm({ ...form, entry_point: e.target.value })}
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
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  <Plus size={15} />
                  Đăng ký bộ kết nối
                </button>
                <button type="button" className="btn" onClick={resetForm}>
                  <X size={15} />
                  Xoá form
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Danh sách bộ kết nối ({connectors.length})</h2>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              style={{ width: "auto" }}
            >
              <option value="">Tất cả loại</option>
              {CONNECTOR_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
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
          ) : connectors.length === 0 ? (
            <div className="empty-state">Chưa có bộ kết nối nào. Đăng ký bộ kết nối đầu tiên ở trên.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mã</th>
                  <th>Tên</th>
                  <th>Loại</th>
                  <th>Phiên bản</th>
                  <th>Giao diện</th>
                  <th>Số lần khởi động lại</th>
                  <th>Trạng thái</th>
                  <th>Cập nhật phiên bản</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {connectors.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.code}</td>
                    <td>
                      {c.name}
                      {c.description && (
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {c.description}
                        </div>
                      )}
                    </td>
                    <td>{connectorTypeLabel(c.connector_type)}</td>
                    <td>{c.version}</td>
                    <td>
                      <span className={`badge ${INTERFACE_BADGE[c.interface_status] || "badge-neutral"}`}>
                        {c.interface_status === "PASSED" ? "Hợp lệ" : "Không hợp lệ"}
                      </span>
                    </td>
                    <td>{c.restart_count}</td>
                    <td>
                      <span className={`badge ${c.is_active ? "badge-success" : "badge-neutral"}`}>
                        {c.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <input
                          placeholder="Phiên bản mới"
                          style={{ width: 110 }}
                          value={versionDrafts[c.id] || ""}
                          onChange={(e) =>
                            setVersionDrafts((prev) => ({ ...prev, [c.id]: e.target.value }))
                          }
                        />
                        <button
                          className="icon-btn"
                          title="Cập nhật phiên bản (khởi động lại luân phiên)"
                          onClick={() => handleUpdateVersion(c)}
                        >
                          <RefreshCw size={15} />
                        </button>
                      </div>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-btn"
                          title={c.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                          onClick={() => handleToggleActive(c)}
                        >
                          {c.is_active ? <PowerOff size={15} /> : <Power size={15} />}
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