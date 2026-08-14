import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Copy, KeyRound, RefreshCw, RotateCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  createApiKey,
  listApiKeys,
  listApiKeyUsageLogs,
  logApiKeyUsage,
  revokeApiKey,
  rotateApiKey,
} from "../../api/apiKeys.js";

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const STATUS_LABEL = {
  ACTIVE: "Đang hoạt động",
  REVOKED: "Đã thu hồi",
  ROTATED: "Đã luân chuyển (còn ân hạn)",
};

const EMPTY_CREATE_FORM = {
  consumer_name: "",
  consumer_code: "",
  description: "",
  scope: "",
};

const EMPTY_USAGE_FORM = {
  endpoint_path: "",
  method: "GET",
  status_code: "",
  consumer_ip: "",
  note: "",
};

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [consumerCodeFilter, setConsumerCodeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [usageLogs, setUsageLogs] = useState([]);

  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [usageForm, setUsageForm] = useState(EMPTY_USAGE_FORM);
  const [gracePeriodDays, setGracePeriodDays] = useState(7);
  const [rotationMode, setRotationMode] = useState("MANUAL");

  const [lastIssuedKey, setLastIssuedKey] = useState(null); // { label, raw_key }
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedKey = keys.find((k) => k.id === selectedId) || null;

  async function loadKeys(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listApiKeys({
        consumerCode: consumerCodeFilter || null,
        status: statusFilter || null,
      });
      const safeData = Array.isArray(data) ? data : [];
      setKeys(safeData);
      if (!keepSelection || !safeData.some((k) => k.id === selectedId)) {
        setSelectedId(safeData.length > 0 ? safeData[0].id : null);
      }
      setError(Array.isArray(data) ? null : "Không tải được danh sách khoá API (phản hồi không hợp lệ)");
    } catch (err) {
      setKeys([]);
      setError(err?.response?.data?.detail?.message || "Không tải được danh sách khoá API");
    } finally {
      setLoading(false);
    }
  }

  async function loadUsageLogs(keyId) {
    if (!keyId) {
      setUsageLogs([]);
      return;
    }
    try {
      const data = await listApiKeyUsageLogs(keyId, 50);
      setUsageLogs(Array.isArray(data) ? data : []);
    } catch {
      setUsageLogs([]);
    }
  }

  useEffect(() => {
    loadKeys(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consumerCodeFilter, statusFilter]);

  useEffect(() => {
    loadUsageLogs(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  // Bước 1 — Tạo khoá API cho đơn vị khai thác -> hệ thống sinh khoá + phạm vi.
  async function handleCreate(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    try {
      const created = await createApiKey(createForm);
      setInfo(`Đã tạo khoá API cho "${created.consumer_name}" (${created.consumer_code}).`);
      setLastIssuedKey({
        label: `Khoá mới cho ${created.consumer_code}`,
        raw_key: created.raw_key,
      });
      setCreateForm(EMPTY_CREATE_FORM);
      await loadKeys(false);
      setSelectedId(created.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Tạo khoá API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 2 — Thu hồi khoá API -> hệ thống thu hồi.
  async function handleRevoke(keyId) {
    clearMessages();
    setSubmitting(true);
    try {
      await revokeApiKey(keyId);
      setInfo("Đã thu hồi khoá API.");
      await loadKeys(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Thu hồi khoá API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 3 — Luân chuyển khoá API (tự động / thủ công) -> hệ thống tạo khoá
  // mới + thời gian ân hạn.
  async function handleRotate(keyId) {
    clearMessages();
    setSubmitting(true);
    try {
      const result = await rotateApiKey(keyId, {
        gracePeriodDays: gracePeriodDays === "" ? null : Number(gracePeriodDays),
        rotationMode,
      });
      setInfo(
        `Đã luân chuyển khoá API -> khoá mới #${result.new_key.id} (ân hạn khoá cũ đến ${formatTime(
          result.old_key.grace_expires_at
        )}).`
      );
      setLastIssuedKey({
        label: `Khoá mới sau luân chuyển (${result.new_key.consumer_code})`,
        raw_key: result.new_key.raw_key,
      });
      await loadKeys(false);
      setSelectedId(result.new_key.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Luân chuyển khoá API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 4 — Ghi nhật ký sử dụng khoá API -> hệ thống ghi nhật ký.
  async function handleLogUsage(e) {
    e.preventDefault();
    if (!selectedKey) return;
    clearMessages();
    setSubmitting(true);
    try {
      const payload = {
        ...usageForm,
        status_code: usageForm.status_code === "" ? null : Number(usageForm.status_code),
      };
      await logApiKeyUsage(selectedKey.id, payload);
      setInfo("Đã ghi nhật ký sử dụng khoá API.");
      setUsageForm(EMPTY_USAGE_FORM);
      await loadUsageLogs(selectedKey.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Ghi nhật ký sử dụng thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  function handleCopyRawKey() {
    if (!lastIssuedKey) return;
    navigator.clipboard?.writeText(lastIssuedKey.raw_key).catch(() => {});
    setInfo("Đã sao chép khoá API vào clipboard.");
  }

  return (
    <AppLayout
      title="Quản lý API key"
      subtitle="UC-059 — Tạo khoá API cho đơn vị khai thác (sinh khoá + phạm vi); thu hồi khoá; luân chuyển khoá (tự động/thủ công) kèm thời gian ân hạn; ghi nhật ký sử dụng khoá."
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
      {lastIssuedKey && (
        <div className="alert alert-info" style={{ marginBottom: 12 }}>
          <KeyRound size={16} />
          <span>
            <strong>{lastIssuedKey.label}</strong> — khoá thật CHỈ hiển thị 1 lần duy nhất, hãy sao
            chép và lưu lại ngay:
            <code style={{ marginLeft: 6, marginRight: 6 }}>{lastIssuedKey.raw_key}</code>
            <button className="icon-btn" title="Sao chép" onClick={handleCopyRawKey}>
              <Copy size={14} />
            </button>
            <button
              className="icon-btn"
              title="Đóng"
              onClick={() => setLastIssuedKey(null)}
              style={{ marginLeft: 4 }}
            >
              ✕
            </button>
          </span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        {/* ---------- Cột trái: danh sách khoá API ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Danh sách khoá API</h2>
            <button className="icon-btn" title="Tải lại" onClick={() => loadKeys(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="consumer-code-filter">Mã đơn vị khai thác</label>
                <input
                  id="consumer-code-filter"
                  value={consumerCodeFilter}
                  onChange={(e) => setConsumerCodeFilter(e.target.value)}
                  placeholder="vd: DVKT-01"
                />
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
                  <option value="ROTATED">Đã luân chuyển (còn ân hạn)</option>
                  <option value="REVOKED">Đã thu hồi</option>
                </select>
              </div>
            </div>

            {loading && <p>Đang tải…</p>}
            {!loading && keys.length === 0 && <p>Chưa có khoá API nào.</p>}

            {!loading && keys.length > 0 && (
              <table className="table">
                <thead>
                  <tr>
                    <th>Đơn vị khai thác</th>
                    <th>Khoá (prefix)</th>
                    <th>Phạm vi</th>
                    <th>Trạng thái</th>
                    <th>Ân hạn đến</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((k) => (
                    <tr
                      key={k.id}
                      onClick={() => setSelectedId(k.id)}
                      style={{
                        cursor: "pointer",
                        background: k.id === selectedId ? "var(--row-active, #eef2ff)" : undefined,
                      }}
                    >
                      <td>
                        {k.consumer_name}
                        <div style={{ fontSize: 12, opacity: 0.7 }}>{k.consumer_code}</div>
                      </td>
                      <td>
                        <code>{k.key_prefix}…</code>
                      </td>
                      <td>{k.scope}</td>
                      <td>
                        <span
                          className={`badge ${
                            k.status === "ACTIVE"
                              ? "badge-success"
                              : k.status === "ROTATED"
                              ? "badge-warning"
                              : "badge-neutral"
                          }`}
                        >
                          {STATUS_LABEL[k.status] || k.status}
                        </span>
                      </td>
                      <td>{formatTime(k.grace_expires_at)}</td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {k.status === "ACTIVE" && (
                          <>
                            <button
                              className="btn btn-secondary"
                              disabled={submitting}
                              onClick={() => handleRotate(k.id)}
                              title="Luân chuyển khoá"
                            >
                              <RotateCw size={13} /> Luân chuyển
                            </button>{" "}
                            <button
                              className="btn btn-danger-ghost"
                              disabled={submitting}
                              onClick={() => handleRevoke(k.id)}
                              title="Thu hồi khoá"
                            >
                              Thu hồi
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Cột phải: tạo khoá + luân chuyển + nhật ký ---------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2>Tạo khoá API mới</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleCreate} className="form-grid">
                <div className="field">
                  <label htmlFor="consumer-name">Tên đơn vị khai thác</label>
                  <input
                    id="consumer-name"
                    required
                    value={createForm.consumer_name}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, consumer_name: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="consumer-code">Mã đơn vị khai thác</label>
                  <input
                    id="consumer-code"
                    required
                    value={createForm.consumer_code}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, consumer_code: e.target.value }))
                    }
                    placeholder="vd: DVKT-01"
                  />
                </div>
                <div className="field">
                  <label htmlFor="scope">Phạm vi (scope)</label>
                  <input
                    id="scope"
                    required
                    value={createForm.scope}
                    onChange={(e) => setCreateForm((f) => ({ ...f, scope: e.target.value }))}
                    placeholder="vd: SEARCH,QA"
                  />
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="description">Mô tả</label>
                  <textarea
                    id="description"
                    rows={2}
                    value={createForm.description}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    Sinh khoá + phạm vi
                  </button>
                </div>
              </form>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Luân chuyển khoá (áp dụng cho khoá đang chọn)</h2>
            </div>
            <div className="card-body">
              {!selectedKey && <p>Chọn 1 khoá API ở bảng bên trái.</p>}
              {selectedKey && (
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="grace-period">Thời gian ân hạn (ngày)</label>
                    <input
                      id="grace-period"
                      type="number"
                      min={0}
                      max={365}
                      value={gracePeriodDays}
                      onChange={(e) => setGracePeriodDays(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="rotation-mode">Phương thức</label>
                    <select
                      id="rotation-mode"
                      value={rotationMode}
                      onChange={(e) => setRotationMode(e.target.value)}
                    >
                      <option value="MANUAL">Thủ công</option>
                      <option value="AUTO">Tự động</option>
                    </select>
                  </div>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <button
                      className="btn"
                      disabled={submitting || selectedKey.status !== "ACTIVE"}
                      onClick={() => handleRotate(selectedKey.id)}
                    >
                      <RotateCw size={14} /> Luân chuyển khoá #{selectedKey.id}
                    </button>
                    {selectedKey.status !== "ACTIVE" && (
                      <p style={{ fontSize: 12, opacity: 0.7, marginTop: 6 }}>
                        Chỉ khoá đang ACTIVE mới luân chuyển được.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Nhật ký sử dụng khoá API</h2>
            </div>
            <div className="card-body">
              {!selectedKey && <p>Chọn 1 khoá API ở bảng bên trái.</p>}
              {selectedKey && (
                <>
                  <form onSubmit={handleLogUsage} className="form-grid" style={{ marginBottom: 12 }}>
                    <div className="field">
                      <label htmlFor="usage-endpoint">Điểm cuối gọi</label>
                      <input
                        id="usage-endpoint"
                        required
                        value={usageForm.endpoint_path}
                        onChange={(e) =>
                          setUsageForm((f) => ({ ...f, endpoint_path: e.target.value }))
                        }
                        placeholder="/v1/search/documents"
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="usage-method">Method</label>
                      <select
                        id="usage-method"
                        value={usageForm.method}
                        onChange={(e) => setUsageForm((f) => ({ ...f, method: e.target.value }))}
                      >
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                        <option value="DELETE">DELETE</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="usage-status">Mã trạng thái HTTP</label>
                      <input
                        id="usage-status"
                        type="number"
                        value={usageForm.status_code}
                        onChange={(e) =>
                          setUsageForm((f) => ({ ...f, status_code: e.target.value }))
                        }
                        placeholder="200"
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="usage-ip">IP đơn vị gọi</label>
                      <input
                        id="usage-ip"
                        value={usageForm.consumer_ip}
                        onChange={(e) =>
                          setUsageForm((f) => ({ ...f, consumer_ip: e.target.value }))
                        }
                        placeholder="10.0.0.5"
                      />
                    </div>
                    <div style={{ gridColumn: "1 / -1" }}>
                      <button className="btn" type="submit" disabled={submitting}>
                        Ghi nhật ký
                      </button>
                    </div>
                  </form>

                  {usageLogs.length === 0 && <p>Chưa có nhật ký sử dụng.</p>}
                  {usageLogs.length > 0 && (
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Thời điểm</th>
                          <th>Method</th>
                          <th>Điểm cuối</th>
                          <th>HTTP</th>
                        </tr>
                      </thead>
                      <tbody>
                        {usageLogs.map((log) => (
                          <tr key={log.id}>
                            <td>{formatTime(log.called_at)}</td>
                            <td>{log.method}</td>
                            <td>{log.endpoint_path}</td>
                            <td>{log.status_code ?? "—"}</td>
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
      </div>
    </AppLayout>
  );
}