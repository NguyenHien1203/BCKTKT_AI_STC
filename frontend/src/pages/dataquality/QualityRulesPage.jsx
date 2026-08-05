import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Gauge,
  History,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  QUALITY_RULE_TYPES,
  createQualityRule,
  getQualityScoreConfigByDataset,
  listQualityRuleVersions,
  listQualityRules,
  listQualityScoreConfigVersions,
  saveQualityScoreConfig,
  updateQualityRule,
} from "../../api/qualityRules.js";

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function ruleTypeLabel(type) {
  return QUALITY_RULE_TYPES.find((t) => t.value === type)?.label || type;
}

function paramsFieldsForType(ruleType) {
  if (ruleType === "VALIDITY") return ["regex", "allowed_values", "min_value", "max_value"];
  if (ruleType === "CONSISTENCY") return ["expression"];
  return [];
}

function buildParams(ruleType, rawParams) {
  const params = {};
  if (ruleType === "VALIDITY") {
    if (rawParams.regex?.trim()) params.regex = rawParams.regex.trim();
    if (rawParams.allowed_values?.trim()) {
      params.allowed_values = rawParams.allowed_values
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean);
    }
    if (rawParams.min_value !== "" && rawParams.min_value != null) {
      params.min_value = Number(rawParams.min_value);
    }
    if (rawParams.max_value !== "" && rawParams.max_value != null) {
      params.max_value = Number(rawParams.max_value);
    }
  }
  if (ruleType === "CONSISTENCY" && rawParams.expression?.trim()) {
    params.expression = rawParams.expression.trim();
  }
  return params;
}

const EMPTY_RAW_PARAMS = { regex: "", allowed_values: "", min_value: "", max_value: "", expression: "" };
const EMPTY_CREATE_FORM = {
  field_names: "",
  rule_type: "COMPLETENESS",
  dataset_id: "",
  weight: "1",
  description: "",
  is_active: true,
  note: "",
  raw_params: EMPTY_RAW_PARAMS,
};
const EMPTY_EDIT_FORM = {
  field_names: "",
  weight: "1",
  description: "",
  is_active: true,
  note: "",
  raw_params: EMPTY_RAW_PARAMS,
};
const RULE_TYPE_KEYS = ["COMPLETENESS", "VALIDITY", "UNIQUENESS", "CONSISTENCY"];
const EMPTY_SCORE_FORM = {
  dataset_id: "",
  pass_threshold: "80",
  weights: { COMPLETENESS: "0.25", VALIDITY: "0.25", UNIQUENESS: "0.25", CONSISTENCY: "0.25" },
};

export default function QualityRulesPage() {
  const [ruleTypeFilter, setRuleTypeFilter] = useState("");
  const [datasetIdFilter, setDatasetIdFilter] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState("");
  const [rules, setRules] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [activePanel, setActivePanel] = useState("create"); // create | edit

  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);

  const [scoreForm, setScoreForm] = useState(EMPTY_SCORE_FORM);
  const [scoreConfig, setScoreConfig] = useState(null);
  const [scoreVersions, setScoreVersions] = useState([]);
  const [scoreError, setScoreError] = useState(null);
  const [scoreInfo, setScoreInfo] = useState(null);
  const [scoreSubmitting, setScoreSubmitting] = useState(false);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedRule = rules.find((r) => r.id === selectedId) || null;

  async function loadRules(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listQualityRules({
        datasetId: datasetIdFilter.trim() ? Number(datasetIdFilter.trim()) : null,
        ruleType: ruleTypeFilter || null,
        isActive: isActiveFilter === "" ? null : isActiveFilter === "true",
      });
      setRules(data);
      if (!keepSelection || !data.some((r) => r.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(ruleId) {
    if (!ruleId) {
      setVersions([]);
      return;
    }
    try {
      setVersions(await listQualityRuleVersions(ruleId));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadRules(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ruleTypeFilter, datasetIdFilter, isActiveFilter]);

  useEffect(() => {
    loadVersions(selectedId);
    if (selectedRule) {
      setEditForm({
        field_names: selectedRule.field_names.join(", "),
        weight: String(selectedRule.weight),
        description: selectedRule.description || "",
        is_active: selectedRule.is_active,
        note: "",
        raw_params: {
          ...EMPTY_RAW_PARAMS,
          regex: selectedRule.params?.regex || "",
          allowed_values: Array.isArray(selectedRule.params?.allowed_values)
            ? selectedRule.params.allowed_values.join(", ")
            : "",
          min_value: selectedRule.params?.min_value ?? "",
          max_value: selectedRule.params?.max_value ?? "",
          expression: selectedRule.params?.expression || "",
        },
      });
      setActivePanel("edit");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await createQualityRule({
        fieldNames: createForm.field_names.split(",").map((f) => f.trim()).filter(Boolean),
        ruleType: createForm.rule_type,
        datasetId: createForm.dataset_id.trim() ? Number(createForm.dataset_id.trim()) : null,
        params: buildParams(createForm.rule_type, createForm.raw_params),
        weight: Number(createForm.weight) || 1,
        description: createForm.description.trim() || null,
        isActive: createForm.is_active,
        note: createForm.note.trim() || null,
      });
      setInfo(`Đã thêm quy tắc "${ruleTypeLabel(created.rule_type)}" (phiên bản ${created.version}).`);
      setError(null);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadRules(false);
      setSelectedId(created.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!selectedRule) return;
    setSubmitting(true);
    try {
      const updated = await updateQualityRule(selectedRule.id, {
        fieldNames: editForm.field_names.split(",").map((f) => f.trim()).filter(Boolean),
        params: buildParams(selectedRule.rule_type, editForm.raw_params),
        weight: Number(editForm.weight) || 1,
        description: editForm.description.trim() || null,
        isActive: editForm.is_active,
        note: editForm.note.trim() || null,
      });
      setInfo(`Đã sửa quy tắc -- phiên bản mới: ${updated.version}.`);
      setError(null);
      setEditForm((f) => ({ ...f, note: "" }));
      await loadRules(true);
      await loadVersions(selectedRule.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function loadScoreConfig() {
    setScoreError(null);
    try {
      const datasetId = scoreForm.dataset_id.trim() ? Number(scoreForm.dataset_id.trim()) : null;
      const config = await getQualityScoreConfigByDataset(datasetId);
      setScoreConfig(config);
      setScoreForm((f) => ({
        ...f,
        pass_threshold: String(config.pass_threshold),
        weights: {
          COMPLETENESS: String(config.rule_type_weights.COMPLETENESS ?? 0),
          VALIDITY: String(config.rule_type_weights.VALIDITY ?? 0),
          UNIQUENESS: String(config.rule_type_weights.UNIQUENESS ?? 0),
          CONSISTENCY: String(config.rule_type_weights.CONSISTENCY ?? 0),
        },
      }));
      setScoreVersions(await listQualityScoreConfigVersions(config.id));
    } catch (e) {
      setScoreConfig(null);
      setScoreVersions([]);
      if (e?.response?.status !== 404) {
        setScoreError(e?.response?.data?.detail?.message || e.message);
      }
    }
  }

  useEffect(() => {
    loadScoreConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveScoreConfig(e) {
    e.preventDefault();
    setScoreSubmitting(true);
    try {
      const weights = {};
      RULE_TYPE_KEYS.forEach((k) => {
        if (scoreForm.weights[k] !== "") weights[k] = Number(scoreForm.weights[k]);
      });
      const saved = await saveQualityScoreConfig({
        datasetId: scoreForm.dataset_id.trim() ? Number(scoreForm.dataset_id.trim()) : null,
        passThreshold: Number(scoreForm.pass_threshold),
        ruleTypeWeights: weights,
      });
      setScoreInfo(`Đã lưu cấu hình điểm -- phiên bản ${saved.version}.`);
      setScoreError(null);
      setScoreConfig(saved);
      setScoreVersions(await listQualityScoreConfigVersions(saved.id));
    } catch (e2) {
      setScoreError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setScoreSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý quy tắc kiểm tra chất lượng"
      subtitle="UC-038 — Xem danh sách quy tắc chất lượng (đầy đủ/hợp lệ/duy nhất/nhất quán); thêm/sửa quy tắc (hệ thống lưu vào metadata.quality_rules + version); cấu hình ngưỡng + trọng số cho điểm (hệ thống lưu)."
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

      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button
          className={`btn ${ruleTypeFilter === "" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setRuleTypeFilter("")}
        >
          Tất cả
        </button>
        {QUALITY_RULE_TYPES.map((t) => (
          <button
            key={t.value}
            className={`btn ${ruleTypeFilter === t.value ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setRuleTypeFilter(t.value)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 1: Xem danh sách quy tắc chất lượng ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 1 — Danh sách quy tắc</h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadRules(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="dataset-filter">Tập dữ liệu (dataset_id)</label>
                <input
                  id="dataset-filter"
                  placeholder="Bỏ trống để xem cả quy tắc chung"
                  value={datasetIdFilter}
                  onChange={(e) => setDatasetIdFilter(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="active-filter">Trạng thái</label>
                <select
                  id="active-filter"
                  value={isActiveFilter}
                  onChange={(e) => setIsActiveFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  <option value="true">Đang áp dụng</option>
                  <option value="false">Đã tắt</option>
                </select>
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : rules.length === 0 ? (
              <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có quy tắc nào.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Loại</th>
                    <th>Trường</th>
                    <th>Tập dữ liệu</th>
                    <th>Trọng số</th>
                    <th>Trạng thái</th>
                    <th>Phiên bản</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => setSelectedId(r.id)}
                      style={{
                        cursor: "pointer",
                        background: selectedId === r.id ? "var(--color-bg-hover, #f5f7fa)" : undefined,
                      }}
                    >
                      <td>
                        <strong>{ruleTypeLabel(r.rule_type)}</strong>
                      </td>
                      <td>{r.field_names.join(", ")}</td>
                      <td>{r.dataset_id ?? "Chung"}</td>
                      <td>{r.weight}</td>
                      <td>
                        <span className={`badge ${r.is_active ? "badge-success" : "badge-danger"}`}>
                          {r.is_active ? "Đang áp dụng" : "Đã tắt"}
                        </span>
                      </td>
                      <td>v{r.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Bước 2: Thêm / Sửa quy tắc ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>{selectedRule ? `${ruleTypeLabel(selectedRule.rule_type)} — ${selectedRule.field_names.join(", ")}` : "Thêm quy tắc mới"}</h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button
                className={`btn ${activePanel === "create" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("create")}
              >
                Thêm mới
              </button>
              <button
                className={`btn ${activePanel === "edit" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("edit")}
                disabled={!selectedRule}
              >
                Sửa quy tắc
              </button>
            </div>

            {activePanel === "create" && (
              <form onSubmit={handleCreate} className="form-grid">
                <div className="field">
                  <label htmlFor="c-rule-type">Loại quy tắc *</label>
                  <select
                    id="c-rule-type"
                    value={createForm.rule_type}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, rule_type: e.target.value }))
                    }
                  >
                    {QUALITY_RULE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="c-fields">Trường áp dụng * (phân tách bởi dấu phẩy)</label>
                  <input
                    id="c-fields"
                    required
                    placeholder="vd: ten_don_vi hoặc ma_don_vi, nam_ngan_sach"
                    value={createForm.field_names}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, field_names: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-dataset">Tập dữ liệu (dataset_id, tuỳ chọn)</label>
                  <input
                    id="c-dataset"
                    placeholder="Bỏ trống = áp dụng cho mọi tập dữ liệu"
                    value={createForm.dataset_id}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, dataset_id: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-weight">Trọng số (giữa các quy tắc cùng loại)</label>
                  <input
                    id="c-weight"
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={createForm.weight}
                    onChange={(e) => setCreateForm((f) => ({ ...f, weight: e.target.value }))}
                  />
                </div>

                {paramsFieldsForType(createForm.rule_type).includes("regex") && (
                  <div className="field">
                    <label htmlFor="c-regex">Regex hợp lệ</label>
                    <input
                      id="c-regex"
                      placeholder="vd: ^[0-9]{10}$"
                      value={createForm.raw_params.regex}
                      onChange={(e) =>
                        setCreateForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, regex: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(createForm.rule_type).includes("allowed_values") && (
                  <div className="field">
                    <label htmlFor="c-allowed">Giá trị cho phép (phân tách bởi dấu phẩy)</label>
                    <input
                      id="c-allowed"
                      value={createForm.raw_params.allowed_values}
                      onChange={(e) =>
                        setCreateForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, allowed_values: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(createForm.rule_type).includes("min_value") && (
                  <div className="field">
                    <label htmlFor="c-min">Giá trị nhỏ nhất</label>
                    <input
                      id="c-min"
                      type="number"
                      value={createForm.raw_params.min_value}
                      onChange={(e) =>
                        setCreateForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, min_value: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(createForm.rule_type).includes("max_value") && (
                  <div className="field">
                    <label htmlFor="c-max">Giá trị lớn nhất</label>
                    <input
                      id="c-max"
                      type="number"
                      value={createForm.raw_params.max_value}
                      onChange={(e) =>
                        setCreateForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, max_value: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(createForm.rule_type).includes("expression") && (
                  <div className="field field-full">
                    <label htmlFor="c-expr">Biểu thức ràng buộc nhất quán *</label>
                    <input
                      id="c-expr"
                      placeholder="vd: ngay_bat_dau <= ngay_ket_thuc"
                      value={createForm.raw_params.expression}
                      onChange={(e) =>
                        setCreateForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, expression: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}

                <div className="field field-full">
                  <label htmlFor="c-desc">Mô tả</label>
                  <input
                    id="c-desc"
                    value={createForm.description}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-active" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      id="c-active"
                      type="checkbox"
                      checked={createForm.is_active}
                      onChange={(e) =>
                        setCreateForm((f) => ({ ...f, is_active: e.target.checked }))
                      }
                    />
                    Áp dụng ngay
                  </label>
                </div>
                <div className="field field-full">
                  <label htmlFor="c-note">Ghi chú</label>
                  <input
                    id="c-note"
                    value={createForm.note}
                    onChange={(e) => setCreateForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? "Đang lưu..." : "Thêm quy tắc"}
                  </button>
                </div>
              </form>
            )}

            {activePanel === "edit" && selectedRule && (
              <form onSubmit={handleUpdate} className="form-grid">
                <div className="field field-full">
                  <label htmlFor="e-fields">Trường áp dụng (phân tách bởi dấu phẩy)</label>
                  <input
                    id="e-fields"
                    value={editForm.field_names}
                    onChange={(e) => setEditForm((f) => ({ ...f, field_names: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="e-weight">Trọng số</label>
                  <input
                    id="e-weight"
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={editForm.weight}
                    onChange={(e) => setEditForm((f) => ({ ...f, weight: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="e-active" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      id="e-active"
                      type="checkbox"
                      checked={editForm.is_active}
                      onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                    />
                    Đang áp dụng
                  </label>
                </div>

                {paramsFieldsForType(selectedRule.rule_type).includes("regex") && (
                  <div className="field">
                    <label htmlFor="e-regex">Regex hợp lệ</label>
                    <input
                      id="e-regex"
                      value={editForm.raw_params.regex}
                      onChange={(e) =>
                        setEditForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, regex: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(selectedRule.rule_type).includes("allowed_values") && (
                  <div className="field">
                    <label htmlFor="e-allowed">Giá trị cho phép (phân tách bởi dấu phẩy)</label>
                    <input
                      id="e-allowed"
                      value={editForm.raw_params.allowed_values}
                      onChange={(e) =>
                        setEditForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, allowed_values: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(selectedRule.rule_type).includes("min_value") && (
                  <div className="field">
                    <label htmlFor="e-min">Giá trị nhỏ nhất</label>
                    <input
                      id="e-min"
                      type="number"
                      value={editForm.raw_params.min_value}
                      onChange={(e) =>
                        setEditForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, min_value: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(selectedRule.rule_type).includes("max_value") && (
                  <div className="field">
                    <label htmlFor="e-max">Giá trị lớn nhất</label>
                    <input
                      id="e-max"
                      type="number"
                      value={editForm.raw_params.max_value}
                      onChange={(e) =>
                        setEditForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, max_value: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}
                {paramsFieldsForType(selectedRule.rule_type).includes("expression") && (
                  <div className="field field-full">
                    <label htmlFor="e-expr">Biểu thức ràng buộc nhất quán</label>
                    <input
                      id="e-expr"
                      value={editForm.raw_params.expression}
                      onChange={(e) =>
                        setEditForm((f) => ({
                          ...f,
                          raw_params: { ...f.raw_params, expression: e.target.value },
                        }))
                      }
                    />
                  </div>
                )}

                <div className="field field-full">
                  <label htmlFor="e-desc">Mô tả</label>
                  <input
                    id="e-desc"
                    value={editForm.description}
                    onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="e-note">Ghi chú thay đổi</label>
                  <input
                    id="e-note"
                    value={editForm.note}
                    onChange={(e) => setEditForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? "Đang lưu..." : `Lưu (tạo phiên bản v${selectedRule.version + 1})`}
                  </button>
                </div>
              </form>
            )}

            {selectedRule && (
              <>
                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <History size={16} /> Lịch sử phiên bản
                </h3>
                {versions.length === 0 ? (
                  <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có lịch sử.</p>
                ) : (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Phiên bản</th>
                        <th>Trường</th>
                        <th>Trọng số</th>
                        <th>Ghi chú</th>
                        <th>Thời điểm</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id}>
                          <td>v{v.version}</td>
                          <td>{v.field_names.join(", ")}</td>
                          <td>{v.weight}</td>
                          <td>{v.change_note || "—"}</td>
                          <td>{formatTime(v.changed_at)}</td>
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

      {/* ---------- Bước 3: Cấu hình ngưỡng + trọng số cho điểm ---------- */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <h2>
            <Gauge size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Bước 3 — Cấu hình ngưỡng + trọng số cho điểm
          </h2>
        </div>
        <div className="card-body">
          {scoreError && (
            <div className="alert alert-error" style={{ marginBottom: 12 }}>
              <AlertCircle size={16} />
              <span>{scoreError}</span>
            </div>
          )}
          {scoreInfo && (
            <div className="alert alert-success" style={{ marginBottom: 12 }}>
              <CheckCircle2 size={16} />
              <span>{scoreInfo}</span>
            </div>
          )}
          <form onSubmit={handleSaveScoreConfig} className="form-grid">
            <div className="field">
              <label htmlFor="s-dataset">Tập dữ liệu (dataset_id)</label>
              <input
                id="s-dataset"
                placeholder="Bỏ trống = cấu hình mặc định"
                value={scoreForm.dataset_id}
                onChange={(e) => setScoreForm((f) => ({ ...f, dataset_id: e.target.value }))}
                onBlur={loadScoreConfig}
              />
            </div>
            <div className="field">
              <label htmlFor="s-threshold">Ngưỡng đạt để công bố (0-100)</label>
              <input
                id="s-threshold"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={scoreForm.pass_threshold}
                onChange={(e) =>
                  setScoreForm((f) => ({ ...f, pass_threshold: e.target.value }))
                }
              />
            </div>
            {RULE_TYPE_KEYS.map((k) => (
              <div className="field" key={k}>
                <label htmlFor={`s-weight-${k}`}>
                  <SlidersHorizontal size={12} style={{ verticalAlign: "middle", marginRight: 4 }} />
                  Trọng số nhóm "{ruleTypeLabel(k)}"
                </label>
                <input
                  id={`s-weight-${k}`}
                  type="number"
                  min="0"
                  step="0.05"
                  value={scoreForm.weights[k]}
                  onChange={(e) =>
                    setScoreForm((f) => ({
                      ...f,
                      weights: { ...f.weights, [k]: e.target.value },
                    }))
                  }
                />
              </div>
            ))}
            <div className="field field-full">
              <button className="btn btn-primary" type="submit" disabled={scoreSubmitting}>
                {scoreSubmitting
                  ? "Đang lưu..."
                  : scoreConfig
                    ? `Lưu (tạo phiên bản v${scoreConfig.version + 1})`
                    : "Lưu cấu hình mới"}
              </button>
            </div>
          </form>

          {scoreVersions.length > 0 && (
            <>
              <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                <History size={16} /> Lịch sử cấu hình điểm
              </h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Phiên bản</th>
                    <th>Ngưỡng đạt</th>
                    <th>Trọng số theo loại</th>
                    <th>Thời điểm</th>
                  </tr>
                </thead>
                <tbody>
                  {scoreVersions.map((v) => (
                    <tr key={v.id}>
                      <td>v{v.version}</td>
                      <td>{v.pass_threshold}</td>
                      <td>
                        {Object.entries(v.rule_type_weights)
                          .map(([k, val]) => `${ruleTypeLabel(k)}: ${val}`)
                          .join(" · ") || "—"}
                      </td>
                      <td>{formatTime(v.changed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}