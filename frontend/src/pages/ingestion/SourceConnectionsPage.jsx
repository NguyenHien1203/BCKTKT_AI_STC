import { useEffect, useState } from "react";
import {
  AlertCircle,
  Bell,
  KeyRound,
  Plug2,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  X,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import {
  activateCredentialAsset,
  activateSourceConnection,
  checkExpiringCredentials,
  configureSourceConnection,
  deactivateCredentialAsset,
  deactivateSourceConnection,
  listCredentialAssets,
  listSourceConnections,
  registerCredentialAsset,
  rotateCredentialAsset,
  testSourceConnection,
} from "../../api/sourceConnections.js";

const CONNECTION_TYPES = [
  { value: "API", label: "API" },
  { value: "DB", label: "Cơ sở dữ liệu (DB)" },
  { value: "FILE", label: "Tệp (File)" },
];

const ASSET_TYPES = [
  { value: "CERTIFICATE", label: "Certificate" },
  { value: "API_KEY", label: "API key" },
];

const TEST_STATUS_BADGE = {
  UNTESTED: "badge-neutral",
  SUCCESS: "badge-success",
  FAILED: "badge-danger",
};

const TEST_STATUS_LABEL = {
  UNTESTED: "Chưa kiểm thử",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
};

const EMPTY_CONNECTION_FORM = {
  data_source_id: "",
  connection_type: CONNECTION_TYPES[0].value,
  config_text: "{}",
  credentials_text: "{}",
};

const EMPTY_ASSET_FORM = {
  connection_id: "",
  asset_type: ASSET_TYPES[0].value,
  secret_value: "",
  expires_at: "",
  rotation_period_days: 90,
};

function parseJsonSafe(text, onError) {
  try {
    const value = JSON.parse(text || "{}");
    if (typeof value !== "object" || Array.isArray(value) || value === null) {
      throw new Error('Phải là một object JSON, ví dụ: {"host": "..."}');
    }
    return value;
  } catch (e) {
    onError(`JSON không hợp lệ: ${e.message}`);
    return null;
  }
}

export default function SourceConnectionsPage() {
  const [dataSources, setDataSources] = useState([]);
  const [connections, setConnections] = useState([]);
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  const [connectionForm, setConnectionForm] = useState(EMPTY_CONNECTION_FORM);
  const [assetForm, setAssetForm] = useState(EMPTY_ASSET_FORM);
  const [rotateDrafts, setRotateDrafts] = useState({});
  const [daysAhead, setDaysAhead] = useState(30);

  async function reload() {
    setLoading(true);
    try {
      const [ds, conns, creds] = await Promise.all([
        listDataSources({}),
        listSourceConnections({}),
        listCredentialAssets({}),
      ]);
      setDataSources(ds);
      setConnections(conns);
      setAssets(creds);
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

  function connectionLabel(id) {
    const conn = connections.find((c) => c.id === id);
    if (!conn) return `#${id}`;
    const ds = dataSources.find((d) => d.id === conn.data_source_id);
    return `#${id} — ${conn.connection_type}${ds ? ` (${ds.name})` : ""}`;
  }

  // ---------- Cấu hình + kiểm thử kết nối ----------

  async function handleConfigureConnection(e) {
    e.preventDefault();
    setError(null);
    const config = parseJsonSafe(connectionForm.config_text, setError);
    if (config === null) return;
    const credentials = parseJsonSafe(connectionForm.credentials_text, setError);
    if (credentials === null) return;

    try {
      await configureSourceConnection({
        data_source_id: Number(connectionForm.data_source_id),
        connection_type: connectionForm.connection_type,
        config,
        credentials,
      });
      setConnectionForm(EMPTY_CONNECTION_FORM);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleTestConnection(connection) {
    try {
      const updated = await testSourceConnection(connection.id);
      if (updated.last_test_status !== "SUCCESS") {
        setError(`Kết nối #${connection.id} thất bại: ${updated.last_test_message}`);
        setInfo(null);
      } else {
        setError(null);
        setInfo(`Kết nối #${connection.id}: ${updated.last_test_message}`);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleConnectionActive(connection) {
    try {
      if (connection.is_active) {
        await deactivateSourceConnection(connection.id);
      } else {
        await activateSourceConnection(connection.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  // ---------- Certificate/API key ----------

  async function handleRegisterAsset(e) {
    e.preventDefault();
    try {
      await registerCredentialAsset({
        connection_id: Number(assetForm.connection_id),
        asset_type: assetForm.asset_type,
        secret_value: assetForm.secret_value,
        expires_at: new Date(assetForm.expires_at).toISOString(),
        rotation_period_days: Number(assetForm.rotation_period_days) || 90,
      });
      setAssetForm(EMPTY_ASSET_FORM);
      setError(null);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleRotateAsset(asset) {
    const draft = rotateDrafts[asset.id] || {};
    if (!draft.secret_value || !draft.expires_at) {
      setError("Nhập giá trị mới và ngày hết hạn mới trước khi luân chuyển");
      return;
    }
    try {
      await rotateCredentialAsset(asset.id, {
        secret_value: draft.secret_value,
        expires_at: new Date(draft.expires_at).toISOString(),
      });
      setRotateDrafts((prev) => ({ ...prev, [asset.id]: {} }));
      setError(null);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleAssetActive(asset) {
    try {
      if (asset.is_active) {
        await deactivateCredentialAsset(asset.id);
      } else {
        await activateCredentialAsset(asset.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleCheckExpiring() {
    try {
      const alerts = await checkExpiringCredentials(daysAhead);
      setError(null);
      setInfo(
        alerts.length === 0
          ? `Không có certificate/API key nào sắp hết hạn trong ${daysAhead} ngày tới.`
          : `Đã gửi ${alerts.length} cảnh báo qua Alertmanager cho certificate/API key sắp hết hạn.`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Cấu hình kết nối nguồn"
      subtitle="UC-017 — Cấu hình connection (API/DB/File), kiểm thử kết nối, quản lý certificate/API key và cảnh báo trước khi hết hạn."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success" style={{ marginBottom: 16 }}>
          <Bell size={16} />
          <span>{info}</span>
        </div>
      )}

      {/* ---------- Cấu hình connection ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Cấu hình connection (API/DB/File)</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleConfigureConnection}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="data_source_id">Nguồn dữ liệu</label>
                <select
                  id="data_source_id"
                  value={connectionForm.data_source_id}
                  onChange={(e) =>
                    setConnectionForm({ ...connectionForm, data_source_id: e.target.value })
                  }
                  required
                >
                  <option value="">-- Chọn nguồn --</option>
                  {dataSources.map((ds) => (
                    <option key={ds.id} value={ds.id}>
                      {ds.code} — {ds.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="connection_type">Loại kết nối</label>
                <select
                  id="connection_type"
                  value={connectionForm.connection_type}
                  onChange={(e) =>
                    setConnectionForm({ ...connectionForm, connection_type: e.target.value })
                  }
                >
                  {CONNECTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="config_text">Cấu hình (JSON, không nhạy cảm)</label>
                <input
                  id="config_text"
                  placeholder='{"base_url": "https://..."} hoặc {"host":"..","database":".."} hoặc {"path":".."}'
                  value={connectionForm.config_text}
                  onChange={(e) =>
                    setConnectionForm({ ...connectionForm, config_text: e.target.value })
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="credentials_text">Thông tin xác thực (JSON — sẽ được mã hoá)</label>
                <input
                  id="credentials_text"
                  placeholder='{"username":"..","password":".."} hoặc {"api_key":".."}'
                  value={connectionForm.credentials_text}
                  onChange={(e) =>
                    setConnectionForm({ ...connectionForm, credentials_text: e.target.value })
                  }
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  <Plus size={15} />
                  Lưu cấu hình
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setConnectionForm(EMPTY_CONNECTION_FORM)}
                >
                  <X size={15} />
                  Xoá form
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Danh sách kết nối ({connections.length})</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : connections.length === 0 ? (
            <div className="empty-state">Chưa có cấu hình kết nối nào.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nguồn dữ liệu</th>
                  <th>Loại</th>
                  <th>Cấu hình</th>
                  <th>Kết quả kiểm thử gần nhất</th>
                  <th>Trạng thái</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((c) => {
                  const ds = dataSources.find((d) => d.id === c.data_source_id);
                  return (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{ds ? `${ds.code} — ${ds.name}` : c.data_source_id}</td>
                      <td>{c.connection_type}</td>
                      <td style={{ fontSize: 12, maxWidth: 220, wordBreak: "break-all" }}>
                        {JSON.stringify(c.config)}
                      </td>
                      <td>
                        <span
                          className={`badge ${TEST_STATUS_BADGE[c.last_test_status] || "badge-neutral"}`}
                        >
                          {TEST_STATUS_LABEL[c.last_test_status] || c.last_test_status}
                        </span>
                        {c.last_test_message && (
                          <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                            {c.last_test_message}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${c.is_active ? "badge-success" : "badge-neutral"}`}>
                          {c.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-btn"
                            title="Kiểm thử kết nối"
                            onClick={() => handleTestConnection(c)}
                          >
                            <Plug2 size={15} />
                          </button>
                          <button
                            className="icon-btn"
                            title={c.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                            onClick={() => handleToggleConnectionActive(c)}
                          >
                            {c.is_active ? <PowerOff size={15} /> : <Power size={15} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ---------- Certificate/API key ---------- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Quản lý certificate / API key</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleRegisterAsset}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="connection_id">Kết nối</label>
                <select
                  id="connection_id"
                  value={assetForm.connection_id}
                  onChange={(e) => setAssetForm({ ...assetForm, connection_id: e.target.value })}
                  required
                >
                  <option value="">-- Chọn kết nối --</option>
                  {connections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {connectionLabel(c.id)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="asset_type">Loại</label>
                <select
                  id="asset_type"
                  value={assetForm.asset_type}
                  onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}
                >
                  {ASSET_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="secret_value">Nội dung (certificate PEM hoặc API key)</label>
                <input
                  id="secret_value"
                  value={assetForm.secret_value}
                  onChange={(e) => setAssetForm({ ...assetForm, secret_value: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="expires_at">Ngày hết hạn</label>
                <input
                  id="expires_at"
                  type="date"
                  value={assetForm.expires_at}
                  onChange={(e) => setAssetForm({ ...assetForm, expires_at: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="rotation_period_days">Chu kỳ luân chuyển (ngày)</label>
                <input
                  id="rotation_period_days"
                  type="number"
                  min="1"
                  value={assetForm.rotation_period_days}
                  onChange={(e) =>
                    setAssetForm({ ...assetForm, rotation_period_days: e.target.value })
                  }
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  <KeyRound size={15} />
                  Đăng ký
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Certificate/API key ({assets.length})</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <label htmlFor="days_ahead" style={{ fontSize: 13 }}>
              Cảnh báo trước
            </label>
            <input
              id="days_ahead"
              type="number"
              min="1"
              style={{ width: 70 }}
              value={daysAhead}
              onChange={(e) => setDaysAhead(Number(e.target.value) || 30)}
            />
            <span style={{ fontSize: 13 }}>ngày</span>
            <button className="btn" onClick={handleCheckExpiring} type="button">
              <Bell size={15} />
              Quét &amp; gửi cảnh báo
            </button>
          </div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {assets.length === 0 ? (
            <div className="empty-state">
              Chưa có certificate/API key nào. Đăng ký ở form phía trên.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Kết nối</th>
                  <th>Loại</th>
                  <th>Hết hạn</th>
                  <th>Số lần luân chuyển</th>
                  <th>Trạng thái</th>
                  <th>Luân chuyển (rotate)</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((a) => (
                  <tr key={a.id}>
                    <td>{a.id}</td>
                    <td>{connectionLabel(a.connection_id)}</td>
                    <td>{ASSET_TYPES.find((t) => t.value === a.asset_type)?.label || a.asset_type}</td>
                    <td>{new Date(a.expires_at).toLocaleDateString("vi-VN")}</td>
                    <td>{a.rotation_count}</td>
                    <td>
                      <span className={`badge ${a.is_active ? "badge-success" : "badge-neutral"}`}>
                        {a.is_active ? "Hoạt động" : "Đã vô hiệu hoá"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <input
                          placeholder="Giá trị mới"
                          style={{ width: 100 }}
                          value={rotateDrafts[a.id]?.secret_value || ""}
                          onChange={(e) =>
                            setRotateDrafts((prev) => ({
                              ...prev,
                              [a.id]: { ...prev[a.id], secret_value: e.target.value },
                            }))
                          }
                        />
                        <input
                          type="date"
                          style={{ width: 130 }}
                          value={rotateDrafts[a.id]?.expires_at || ""}
                          onChange={(e) =>
                            setRotateDrafts((prev) => ({
                              ...prev,
                              [a.id]: { ...prev[a.id], expires_at: e.target.value },
                            }))
                          }
                        />
                        <button
                          className="icon-btn"
                          title="Luân chuyển"
                          onClick={() => handleRotateAsset(a)}
                        >
                          <RefreshCw size={15} />
                        </button>
                      </div>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-btn"
                          title={a.is_active ? "Vô hiệu hoá" : "Kích hoạt"}
                          onClick={() => handleToggleAssetActive(a)}
                        >
                          {a.is_active ? <PowerOff size={15} /> : <Power size={15} />}
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