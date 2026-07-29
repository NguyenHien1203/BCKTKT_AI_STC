import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Database,
  KeyRound,
  Layers,
  Plus,
  Power,
  PowerOff,
  Rows3,
  Trash2,
  X,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import {
  activateDataset,
  configurePartitioning,
  declareCriticalFields,
  deactivateDataset,
  defineDataset,
  getDataset,
  listCriticalFields,
  listDatasets,
  listSchemaVersions,
  registerSchemaVersion,
  updateDatasetSchema,
} from "../../api/datasets.js";

const DATA_TYPES = ["STRING", "INTEGER", "BIGINT", "DECIMAL", "BOOLEAN", "DATE", "DATETIME", "JSON"];
const PARTITION_STRATEGIES = [
  { value: "NONE", label: "Không phân mảnh" },
  { value: "RANGE", label: "RANGE (theo khoảng)" },
  { value: "LIST", label: "LIST (theo danh sách giá trị)" },
  { value: "HASH", label: "HASH" },
];

const EMPTY_FIELD = { name: "", data_type: "STRING", nullable: true, description: "" };
const EMPTY_DEFINE_FORM = {
  data_source_id: "",
  code: "",
  name: "",
  description: "",
  schema_fields: [{ ...EMPTY_FIELD }],
};

function errMsg(e) {
  return e?.response?.data?.detail?.message || e.message;
}

export default function DatasetsPage() {
  const [dataSources, setDataSources] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterDataSource, setFilterDataSource] = useState("");
  const [onlyActive, setOnlyActive] = useState(false);

  const [defineForm, setDefineForm] = useState(EMPTY_DEFINE_FORM);
  const [showDefineForm, setShowDefineForm] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [criticalFields, setCriticalFields] = useState([]);
  const [schemaVersions, setSchemaVersions] = useState([]);

  const [pkDraft, setPkDraft] = useState([]);
  const [partitionStrategyDraft, setPartitionStrategyDraft] = useState("NONE");
  const [partitionColumnDraft, setPartitionColumnDraft] = useState("");
  const [criticalDraft, setCriticalDraft] = useState([]);

  function notify(setter, message) {
    setter(message);
    setTimeout(() => setter(null), 4000);
  }

  async function reloadList() {
    setLoading(true);
    try {
      const [ds, list] = await Promise.all([
        listDataSources({}),
        listDatasets({ dataSourceId: filterDataSource || null, onlyActive }),
      ]);
      setDataSources(ds);
      setDatasets(list);
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }

  async function reloadDetail(id) {
    if (!id) {
      setSelected(null);
      setCriticalFields([]);
      setSchemaVersions([]);
      return;
    }
    try {
      const [ds, crit, versions] = await Promise.all([
        getDataset(id),
        listCriticalFields(id),
        listSchemaVersions(id),
      ]);
      setSelected(ds);
      setCriticalFields(crit);
      setSchemaVersions(versions);
      setPkDraft(ds.primary_key || []);
      setPartitionStrategyDraft(ds.partition_strategy || "NONE");
      setPartitionColumnDraft(ds.partition_column || "");
      setCriticalDraft(crit.map((f) => f.field_name));
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  useEffect(() => {
    reloadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterDataSource, onlyActive]);

  useEffect(() => {
    reloadDetail(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function dataSourceLabel(id) {
    return dataSources.find((d) => d.id === id)?.name || `#${id}`;
  }

  // ---------- Bước 1: Định nghĩa tập dữ liệu + lược đồ ----------

  function updateFieldRow(idx, patch) {
    setDefineForm((f) => ({
      ...f,
      schema_fields: f.schema_fields.map((row, i) => (i === idx ? { ...row, ...patch } : row)),
    }));
  }

  function addFieldRow() {
    setDefineForm((f) => ({ ...f, schema_fields: [...f.schema_fields, { ...EMPTY_FIELD }] }));
  }

  function removeFieldRow(idx) {
    setDefineForm((f) => ({
      ...f,
      schema_fields: f.schema_fields.filter((_, i) => i !== idx),
    }));
  }

  async function handleDefineSubmit(e) {
    e.preventDefault();
    try {
      const payload = {
        data_source_id: Number(defineForm.data_source_id),
        code: defineForm.code,
        name: defineForm.name,
        description: defineForm.description,
        schema_fields: defineForm.schema_fields,
      };
      const created = await defineDataset(payload);
      setDefineForm(EMPTY_DEFINE_FORM);
      setShowDefineForm(false);
      await reloadList();
      setSelectedId(created.id);
      notify(setInfo, `Đã định nghĩa tập dữ liệu "${created.name}" (lược đồ ${created.schema_fields.length} trường).`);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  async function handleToggleActive(ds) {
    try {
      if (ds.is_active) {
        await deactivateDataset(ds.id);
      } else {
        await activateDataset(ds.id);
      }
      await reloadList();
      if (selectedId === ds.id) await reloadDetail(ds.id);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  // ---------- Bước 2: Khoá chính + chiến lược phân mảnh ----------

  function togglePkDraft(name) {
    setPkDraft((prev) => (prev.includes(name) ? prev.filter((f) => f !== name) : [...prev, name]));
  }

  async function handleSavePartitioning() {
    if (!selected) return;
    try {
      const updated = await configurePartitioning(selected.id, {
        primaryKey: pkDraft,
        partitionStrategy: partitionStrategyDraft,
        partitionColumn: partitionStrategyDraft !== "NONE" ? partitionColumnDraft : null,
      });
      setSelected(updated);
      await reloadList();
      notify(setInfo, "Đã lưu khoá chính + chiến lược phân mảnh.");
    } catch (e) {
      setError(errMsg(e));
    }
  }

  // ---------- Bước 3: Trường bắt buộc (NOT NULL) ----------

  function toggleCriticalDraft(name) {
    setCriticalDraft((prev) =>
      prev.includes(name) ? prev.filter((f) => f !== name) : [...prev, name]
    );
  }

  async function handleSaveCriticalFields() {
    if (!selected) return;
    try {
      const saved = await declareCriticalFields(selected.id, criticalDraft);
      setCriticalFields(saved);
      notify(setInfo, `Đã lưu ${saved.length} trường bắt buộc (NOT NULL).`);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  // ---------- Bước 4: Đăng ký Schema Registry ----------

  async function handleRegisterSchema() {
    if (!selected) return;
    try {
      const version = await registerSchemaVersion(selected.id);
      await reloadDetail(selected.id);
      notify(setInfo, `Đã đăng ký Schema Registry — phiên bản lược đồ v${version.version}.`);
    } catch (e) {
      setError(errMsg(e));
    }
  }

  return (
    <AppLayout
      title="Định nghĩa tập dữ liệu của nguồn"
      subtitle="UC-018 — Lược đồ, khoá chính + phân mảnh, trường bắt buộc (NOT NULL), đăng ký Schema Registry."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{info}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Bước 1 — Định nghĩa tập dữ liệu + lược đồ</h2>
          {!showDefineForm && (
            <button className="btn btn-primary" onClick={() => setShowDefineForm(true)}>
              <Plus size={15} />
              Định nghĩa tập dữ liệu mới
            </button>
          )}
        </div>
        {showDefineForm && (
          <div className="card-body">
            <form onSubmit={handleDefineSubmit}>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="data_source_id">Nguồn dữ liệu</label>
                  <select
                    id="data_source_id"
                    value={defineForm.data_source_id}
                    onChange={(e) => setDefineForm({ ...defineForm, data_source_id: e.target.value })}
                    required
                  >
                    <option value="">-- Chọn nguồn dữ liệu --</option>
                    {dataSources.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="ds_code">Mã tập dữ liệu</label>
                  <input
                    id="ds_code"
                    value={defineForm.code}
                    onChange={(e) => setDefineForm({ ...defineForm, code: e.target.value })}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="ds_name">Tên tập dữ liệu</label>
                  <input
                    id="ds_name"
                    value={defineForm.name}
                    onChange={(e) => setDefineForm({ ...defineForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="ds_desc">Mô tả</label>
                  <input
                    id="ds_desc"
                    value={defineForm.description}
                    onChange={(e) => setDefineForm({ ...defineForm, description: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <strong>Lược đồ (schema)</strong>
                  <button type="button" className="btn" onClick={addFieldRow}>
                    <Plus size={14} />
                    Thêm trường
                  </button>
                </div>
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
                    {defineForm.schema_fields.map((row, idx) => (
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
                          {defineForm.schema_fields.length > 1 && (
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
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button type="submit" className="btn btn-primary">
                  <Plus size={15} />
                  Lưu định nghĩa tập dữ liệu
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setShowDefineForm(false);
                    setDefineForm(EMPTY_DEFINE_FORM);
                  }}
                >
                  <X size={15} />
                  Huỷ
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 1fr) 2fr", gap: 20, alignItems: "start" }}>
        <div className="card">
          <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
            <h2>Danh sách tập dữ liệu ({datasets.length})</h2>
          </div>
          <div className="card-body" style={{ padding: 12 }}>
            <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
              <select
                value={filterDataSource}
                onChange={(e) => setFilterDataSource(e.target.value)}
                style={{ width: "auto" }}
              >
                <option value="">Tất cả nguồn dữ liệu</option>
                {dataSources.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code}
                  </option>
                ))}
              </select>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                <input type="checkbox" checked={onlyActive} onChange={(e) => setOnlyActive(e.target.checked)} />
                Chỉ hiện đang hoạt động
              </label>
            </div>
            {loading ? (
              <div className="empty-state">Đang tải dữ liệu...</div>
            ) : datasets.length === 0 ? (
              <div className="empty-state">Chưa có tập dữ liệu nào.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {datasets.map((ds) => (
                  <button
                    key={ds.id}
                    onClick={() => setSelectedId(ds.id)}
                    className="card"
                    style={{
                      textAlign: "left",
                      padding: 12,
                      border: selectedId === ds.id ? "2px solid var(--color-primary)" : undefined,
                      cursor: "pointer",
                      background: "none",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <strong>{ds.name}</strong>
                      <span className={`badge ${ds.is_active ? "badge-success" : "badge-neutral"}`}>
                        {ds.is_active ? "Hoạt động" : "Vô hiệu hoá"}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      {ds.code} · {dataSourceLabel(ds.data_source_id)}
                    </div>
                    <div style={{ fontSize: 12, marginTop: 4 }}>
                      Schema v{ds.current_schema_version} · {ds.schema_fields.length} trường
                      {ds.primary_key.length > 0 ? ` · PK: ${ds.primary_key.join(", ")}` : ""}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          {!selected ? (
            <div className="card">
              <div className="card-body empty-state">
                Chọn 1 tập dữ liệu ở danh sách bên trái để cấu hình khoá chính, trường bắt buộc và đăng ký Schema Registry.
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="card">
                <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
                  <h2>
                    <Database size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
                    {selected.name} <span style={{ color: "var(--color-text-secondary)" }}>({selected.code})</span>
                  </h2>
                  <button className="icon-btn" title={selected.is_active ? "Vô hiệu hoá" : "Kích hoạt"} onClick={() => handleToggleActive(selected)}>
                    {selected.is_active ? <PowerOff size={15} /> : <Power size={15} />}
                  </button>
                </div>
                <div className="card-body">
                  <p style={{ marginTop: 0 }}>{selected.description || "—"}</p>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Tên trường</th>
                        <th>Kiểu dữ liệu</th>
                        <th>NULL?</th>
                        <th>Mô tả</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.schema_fields.map((f) => (
                        <tr key={f.name}>
                          <td>{f.name}</td>
                          <td>{f.data_type}</td>
                          <td>{f.nullable ? "Có" : "Không"}</td>
                          <td>{f.description || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h2>
                    <KeyRound size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
                    Bước 2 — Khoá chính + chiến lược phân mảnh
                  </h2>
                </div>
                <div className="card-body">
                  <div className="field" style={{ marginBottom: 12 }}>
                    <label>Khoá chính (chọn 1 hoặc nhiều trường)</label>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                      {selected.schema_fields.map((f) => (
                        <label key={f.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                          <input
                            type="checkbox"
                            checked={pkDraft.includes(f.name)}
                            onChange={() => togglePkDraft(f.name)}
                          />
                          {f.name}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="partition_strategy">Chiến lược phân mảnh</label>
                      <select
                        id="partition_strategy"
                        value={partitionStrategyDraft}
                        onChange={(e) => setPartitionStrategyDraft(e.target.value)}
                      >
                        {PARTITION_STRATEGIES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    {partitionStrategyDraft !== "NONE" && (
                      <div className="field">
                        <label htmlFor="partition_column">Cột phân mảnh</label>
                        <select
                          id="partition_column"
                          value={partitionColumnDraft}
                          onChange={(e) => setPartitionColumnDraft(e.target.value)}
                        >
                          <option value="">-- Chọn cột --</option>
                          {selected.schema_fields.map((f) => (
                            <option key={f.name} value={f.name}>
                              {f.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                  <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={handleSavePartitioning}>
                    <KeyRound size={15} />
                    Lưu khoá chính + chiến lược phân mảnh
                  </button>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h2>
                    <Rows3 size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
                    Bước 3 — Trường bắt buộc (NOT NULL)
                  </h2>
                </div>
                <div className="card-body">
                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
                    {selected.schema_fields.map((f) => (
                      <label key={f.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                        <input
                          type="checkbox"
                          checked={criticalDraft.includes(f.name)}
                          onChange={() => toggleCriticalDraft(f.name)}
                        />
                        {f.name}
                      </label>
                    ))}
                  </div>
                  <button className="btn btn-primary" onClick={handleSaveCriticalFields}>
                    <Rows3 size={15} />
                    Lưu trường bắt buộc ({criticalFields.length} hiện có)
                  </button>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h2>
                    <Layers size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
                    Bước 4 — Đăng ký Schema Registry
                  </h2>
                  <button
                    className="btn btn-primary"
                    onClick={handleRegisterSchema}
                    disabled={selected.primary_key.length === 0}
                    title={selected.primary_key.length === 0 ? "Phải khai báo khoá chính (bước 2) trước" : ""}
                  >
                    <ClipboardList size={15} />
                    Đăng ký phiên bản mới
                  </button>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                  {schemaVersions.length === 0 ? (
                    <div className="empty-state">Chưa đăng ký phiên bản lược đồ nào.</div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Phiên bản</th>
                          <th>Khoá chính</th>
                          <th>Phân mảnh</th>
                          <th>Trường bắt buộc</th>
                          <th>Số trường</th>
                          <th>Thời điểm đăng ký</th>
                        </tr>
                      </thead>
                      <tbody>
                        {schemaVersions.map((v) => (
                          <tr key={v.version}>
                            <td>
                              <span className="badge badge-neutral">v{v.version}</span>
                            </td>
                            <td>{(v.schema_snapshot.primary_key || []).join(", ") || "—"}</td>
                            <td>
                              {v.schema_snapshot.partition_strategy}
                              {v.schema_snapshot.partition_column ? ` (${v.schema_snapshot.partition_column})` : ""}
                            </td>
                            <td>{(v.schema_snapshot.critical_fields || []).join(", ") || "—"}</td>
                            <td>{(v.schema_snapshot.schema_fields || []).length}</td>
                            <td>{new Date(v.registered_at).toLocaleString("vi-VN")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}