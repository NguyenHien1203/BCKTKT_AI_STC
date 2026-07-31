import { useEffect, useMemo, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, History, Plus, RefreshCw, Trash2 } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import { getDataset, listDatasets } from "../../api/datasets.js";
import { checkSchemaRegistry, listSchemaRegistryChecks } from "../../api/schemaRegistry.js";

const DATA_TYPES = ["STRING", "INTEGER", "BIGINT", "DECIMAL", "BOOLEAN", "DATE", "DATETIME", "JSON"];
const EMPTY_FIELD = { name: "", data_type: "STRING", nullable: true, description: "" };

const STATUS_BADGE = {
  COMPATIBLE: "badge-success",
  BREAKING: "badge-danger",
};

const STATUS_LABEL = {
  COMPATIBLE: "Tương thích",
  BREAKING: "Phá vỡ tương thích",
};

function errMsg(e) {
  return e?.response?.data?.detail?.message || e.message;
}

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function SchemaRegistryChecksPage() {
  const [dataSources, setDataSources] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [incomingFields, setIncomingFields] = useState([{ ...EMPTY_FIELD }]);
  const [history, setHistory] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);

  async function loadCatalog() {
    setLoading(true);
    try {
      const [sourcesData, datasetsData] = await Promise.all([listDataSources({}), listDatasets({})]);
      setDataSources(sourcesData);
      setDatasets(datasetsData);
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCatalog();
  }, []);

  const sourceById = useMemo(() => new Map(dataSources.map((s) => [s.id, s])), [dataSources]);

  async function loadHistory(datasetId, status) {
    try {
      const checks = await listSchemaRegistryChecks(datasetId, { status: status || null });
      setHistory(checks);
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  // Nạp sẵn lược đồ hiện tại của dataset (mô phỏng lược đồ nguồn đọc được
  // trước khi phân tích) để người dùng chỉnh sửa rồi kiểm tra đối chiếu.
  async function handleSelectDataset(datasetId) {
    setSelectedDatasetId(datasetId);
    setLastResult(null);
    if (!datasetId) {
      setIncomingFields([{ ...EMPTY_FIELD }]);
      setHistory([]);
      return;
    }
    try {
      const dataset = await getDataset(Number(datasetId));
      setIncomingFields(
        (dataset.schema_fields || []).map((f) => ({
          name: f.name,
          data_type: f.data_type,
          nullable: f.nullable,
          description: f.description || "",
        }))
      );
    } catch (e) {
      setError(errMsg(e));
    }
    await loadHistory(Number(datasetId), statusFilter);
  }

  function updateFieldRow(idx, patch) {
    setIncomingFields((rows) => rows.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  }

  function addFieldRow() {
    setIncomingFields((rows) => [...rows, { ...EMPTY_FIELD }]);
  }

  function removeFieldRow(idx) {
    setIncomingFields((rows) => rows.filter((_, i) => i !== idx));
  }

  async function handleCheck(e) {
    e.preventDefault();
    if (!selectedDatasetId) return;
    setChecking(true);
    try {
      const result = await checkSchemaRegistry(Number(selectedDatasetId), {
        schemaFields: incomingFields,
      });
      setLastResult(result);
      setError(null);
      await loadHistory(Number(selectedDatasetId), statusFilter);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setChecking(false);
    }
  }

  async function handleFilterChange(status) {
    setStatusFilter(status);
    if (selectedDatasetId) {
      await loadHistory(Number(selectedDatasetId), status);
    }
  }

  const selectedDataset = datasets.find((d) => d.id === Number(selectedDatasetId));

  return (
    <AppLayout
      title="Kiểm tra Schema Registry"
      subtitle="UC-026 — Trước khi phân tích, hệ thống so sánh lược đồ nguồn với lược đồ đã đăng ký (UC-018). Nếu phá vỡ tương thích: DỪNG quy trình xử lý + cảnh báo Quản trị Tích hợp. Nếu tương thích (chỉ bổ sung): chuyển tiếp + ghi nhận thay đổi."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Chọn tập dữ liệu</h2>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : datasets.length === 0 ? (
            <div className="empty-state">
              Chưa có tập dữ liệu nào. Định nghĩa tập dữ liệu + đăng ký Schema Registry (UC-018)
              trước.
            </div>
          ) : (
            <div className="form-grid">
              <div className="field">
                <label htmlFor="dataset">Tập dữ liệu</label>
                <select
                  id="dataset"
                  value={selectedDatasetId}
                  onChange={(e) => handleSelectDataset(e.target.value)}
                >
                  <option value="" disabled>
                    -- Chọn tập dữ liệu --
                  </option>
                  {datasets.map((d) => {
                    const source = sourceById.get(d.data_source_id);
                    return (
                      <option key={d.id} value={d.id}>
                        [{source ? source.source_system : "?"}] {d.code} — {d.name} (đã đăng ký v
                        {d.current_schema_version})
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedDataset && (
        <form onSubmit={handleCheck}>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Lược đồ nguồn (mô phỏng đọc được trước khi phân tích)</h2>
              <button type="button" className="btn" onClick={addFieldRow}>
                <Plus size={14} />
                Thêm trường
              </button>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {selectedDataset.current_schema_version === 0 ? (
                <div className="empty-state">
                  Tập dữ liệu này chưa đăng ký lược đồ nào vào Schema Registry (UC-018 bước 4) —
                  không có gì để đối chiếu.
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tên trường</th>
                      <th>Kiểu dữ liệu</th>
                      <th>Cho phép NULL</th>
                      <th>Mô tả</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {incomingFields.map((row, idx) => (
                      <tr key={idx}>
                        <td>
                          <input
                            value={row.name}
                            onChange={(e) => updateFieldRow(idx, { name: e.target.value })}
                            required
                          />
                        </td>
                        <td>
                          <select
                            value={row.data_type}
                            onChange={(e) => updateFieldRow(idx, { data_type: e.target.value })}
                          >
                            {DATA_TYPES.map((t) => (
                              <option key={t} value={t}>
                                {t}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            checked={row.nullable}
                            onChange={(e) => updateFieldRow(idx, { nullable: e.target.checked })}
                          />
                        </td>
                        <td>
                          <input
                            value={row.description}
                            onChange={(e) => updateFieldRow(idx, { description: e.target.value })}
                          />
                        </td>
                        <td>
                          {incomingFields.length > 1 && (
                            <button
                              type="button"
                              className="icon-btn"
                              title="Xoá trường"
                              onClick={() => removeFieldRow(idx)}
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {selectedDataset.current_schema_version > 0 && (
            <div style={{ marginBottom: 20 }}>
              <button type="submit" className="btn btn-primary" disabled={checking}>
                <RefreshCw size={15} />
                {checking ? "Đang kiểm tra..." : "So sánh với lược đồ đã đăng ký"}
              </button>
            </div>
          )}
        </form>
      )}

      {lastResult && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả kiểm tra vừa rồi</h2>
            <span className={`badge ${STATUS_BADGE[lastResult.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastResult.status] || lastResult.status}
            </span>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              {lastResult.status === "BREAKING" ? (
                <AlertTriangle size={16} style={{ color: "var(--color-danger)" }} />
              ) : (
                <CheckCircle2 size={16} style={{ color: "var(--color-success)" }} />
              )}
              <span>{lastResult.message}</span>
            </div>
            <p>
              Đối chiếu với phiên bản đã đăng ký <strong>v{lastResult.registered_version}</strong>.
            </p>
            {lastResult.status === "BREAKING" ? (
              <p style={{ color: "var(--color-danger)" }}>
                Hệ thống đã DỪNG quy trình xử lý và cảnh báo Quản trị Tích hợp (phát sự kiện
                <code> schema_registry.compatibility_broken</code>).
              </p>
            ) : (
              <p>
                Hệ thống đã chuyển tiếp sang bước phân tích tiếp theo và ghi nhận thay đổi.
              </p>
            )}
            {lastResult.added_fields.length > 0 && (
              <p>Trường bổ sung: {lastResult.added_fields.join(", ")}</p>
            )}
            {lastResult.removed_fields.length > 0 && (
              <p>Trường bị mất: {lastResult.removed_fields.join(", ")}</p>
            )}
            {lastResult.changed_type_fields.length > 0 && (
              <p>
                Trường đổi kiểu dữ liệu:{" "}
                {lastResult.changed_type_fields
                  .map((c) => `${c.name} (${c.old_type} -> ${c.new_type})`)
                  .join(", ")}
              </p>
            )}
          </div>
        </div>
      )}

      {selectedDataset && (
        <div className="card">
          <div className="card-header">
            <h2>
              <History size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Lịch sử kiểm tra
            </h2>
            <select value={statusFilter} onChange={(e) => handleFilterChange(e.target.value)}>
              <option value="">Tất cả trạng thái</option>
              <option value="COMPATIBLE">Tương thích</option>
              <option value="BREAKING">Phá vỡ tương thích</option>
            </select>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {history.length === 0 ? (
              <div className="empty-state">Chưa có lượt kiểm tra nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Thời điểm</th>
                    <th>Phiên bản đối chiếu</th>
                    <th>Trạng thái</th>
                    <th>Thay đổi</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{formatTime(c.checked_at)}</td>
                      <td>v{c.registered_version}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[c.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[c.status] || c.status}
                        </span>
                      </td>
                      <td>
                        {c.added_fields.length > 0 && <span>+{c.added_fields.length} </span>}
                        {c.removed_fields.length > 0 && <span>-{c.removed_fields.length} </span>}
                        {c.changed_type_fields.length > 0 && (
                          <span>~{c.changed_type_fields.length}</span>
                        )}
                        {c.added_fields.length === 0 &&
                          c.removed_fields.length === 0 &&
                          c.changed_type_fields.length === 0 &&
                          "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}