import { useEffect, useMemo, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Inbox, RefreshCw, XCircle } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import {
  batchResolveQualityExceptions,
  listQualityExceptions,
  resolveQualityException,
} from "../../api/qualityExceptions.js";

const STATUS_BADGE = {
  PENDING: "badge-warning",
  RESOLVED: "badge-success",
};

const STATUS_LABEL = {
  PENDING: "Chưa xử lý",
  RESOLVED: "Đã xử lý",
};

const ACTION_LABEL = {
  FIX: "Đã sửa",
  REJECT: "Từ chối",
  REQUEST_SOURCE: "Yêu cầu nguồn",
};

const RULE_TYPE_LABEL = {
  COMPLETENESS: "Đầy đủ",
  VALIDITY: "Hợp lệ",
  UNIQUENESS: "Duy nhất",
  CONSISTENCY: "Nhất quán",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function failedRuleSummary(item) {
  return (item.failed_rules || [])
    .map((f) => `${RULE_TYPE_LABEL[f.rule_type] || f.rule_type} (${(f.field_names || []).join(", ")}): ${f.reason}`)
    .join(" | ");
}

/** Ô nhập giá trị sửa (bước 2 action=FIX) -- 1 dòng field_name=value, có thể thêm nhiều dòng. */
function CorrectedFieldsEditor({ pairs, onChange }) {
  function updatePair(idx, key, value) {
    const next = pairs.slice();
    next[idx] = { key, value };
    onChange(next);
  }
  function addPair() {
    onChange([...pairs, { key: "", value: "" }]);
  }
  function removePair(idx) {
    onChange(pairs.filter((_, i) => i !== idx));
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {pairs.map((p, idx) => (
        <div key={idx} style={{ display: "flex", gap: 4 }}>
          <input
            type="text"
            placeholder="tên trường"
            value={p.key}
            onChange={(e) => updatePair(idx, e.target.value, p.value)}
            style={{ minWidth: 120 }}
          />
          <input
            type="text"
            placeholder="giá trị mới"
            value={p.value}
            onChange={(e) => updatePair(idx, p.key, e.target.value)}
            style={{ minWidth: 140 }}
          />
          <button type="button" className="icon-btn" title="Bỏ dòng" onClick={() => removePair(idx)}>
            <XCircle size={14} />
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-secondary" onClick={addPair} style={{ alignSelf: "flex-start" }}>
        + Thêm trường sửa
      </button>
    </div>
  );
}

function pairsToFields(pairs) {
  const out = {};
  for (const p of pairs) {
    if (p.key.trim()) out[p.key.trim()] = p.value;
  }
  return out;
}

/** Form xử lý 1 ngoại lệ (bước 2), hiển thị trực tiếp trên dòng bảng. */
function ResolveForm({ item, onResolved, onError }) {
  const [action, setAction] = useState("FIX");
  const [pairs, setPairs] = useState([{ key: "", value: "" }]);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const result = await resolveQualityException(item.id, {
        action,
        correctedFields: action === "FIX" ? pairsToFields(pairs) : null,
        reason: action !== "FIX" ? reason : null,
      });
      onResolved(result);
      onError(null);
    } catch (e) {
      onError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const correctedFields = pairsToFields(pairs);
  const canSubmit =
    !submitting &&
    (action === "FIX" ? Object.keys(correctedFields).length > 0 : reason.trim().length > 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 260 }}>
      <select value={action} onChange={(e) => setAction(e.target.value)}>
        <option value="FIX">Sửa giá trị</option>
        <option value="REJECT">Từ chối</option>
        <option value="REQUEST_SOURCE">Yêu cầu nguồn gửi lại</option>
      </select>
      {action === "FIX" ? (
        <CorrectedFieldsEditor pairs={pairs} onChange={setPairs} />
      ) : (
        <input
          type="text"
          placeholder={action === "REJECT" ? "Lý do từ chối..." : "Lý do yêu cầu nguồn..."}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      )}
      <button className="btn btn-primary" onClick={handleSubmit} disabled={!canSubmit}>
        {submitting ? "Đang lưu..." : "Xử lý"}
      </button>
    </div>
  );
}

/** Card xử lý hàng loạt ngoại lệ cùng loại (bước 3). */
function BatchResolveCard({ datasetId, ruleTypeOptions, onResolved, onError }) {
  const [ruleType, setRuleType] = useState("");
  const [action, setAction] = useState("REJECT");
  const [pairs, setPairs] = useState([{ key: "", value: "" }]);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!ruleType && ruleTypeOptions.length > 0) setRuleType(ruleTypeOptions[0]);
    if (ruleType && !ruleTypeOptions.includes(ruleType)) setRuleType(ruleTypeOptions[0] || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ruleTypeOptions]);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const result = await batchResolveQualityExceptions({
        datasetId,
        ruleType,
        action,
        correctedFields: action === "FIX" ? pairsToFields(pairs) : null,
        reason: action !== "FIX" ? reason : null,
      });
      onResolved(result);
      onError(null);
    } catch (e) {
      onError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const correctedFields = pairsToFields(pairs);
  const canSubmit =
    !submitting &&
    datasetId &&
    ruleType &&
    (action === "FIX" ? Object.keys(correctedFields).length > 0 : reason.trim().length > 0);

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div className="card-header">
        <h2>Bước 3 — Xử lý hàng loạt ngoại lệ cùng loại</h2>
      </div>
      <div className="card-body">
        {!datasetId ? (
          <div className="empty-state">Chọn 1 tập dữ liệu cụ thể ở bộ lọc bên trên để xử lý hàng loạt.</div>
        ) : ruleTypeOptions.length === 0 ? (
          <div className="empty-state">Không có ngoại lệ PENDING nào của tập dữ liệu này.</div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-start" }}>
            <div className="field">
              <label htmlFor="batch-rule-type">Loại quy tắc không đạt</label>
              <select id="batch-rule-type" value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                {ruleTypeOptions.map((rt) => (
                  <option key={rt} value={rt}>
                    {RULE_TYPE_LABEL[rt] || rt}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="batch-action">Quyết định áp dụng</label>
              <select id="batch-action" value={action} onChange={(e) => setAction(e.target.value)}>
                <option value="FIX">Sửa giá trị</option>
                <option value="REJECT">Từ chối</option>
                <option value="REQUEST_SOURCE">Yêu cầu nguồn gửi lại</option>
              </select>
            </div>
            <div style={{ minWidth: 260 }}>
              {action === "FIX" ? (
                <CorrectedFieldsEditor pairs={pairs} onChange={setPairs} />
              ) : (
                <input
                  type="text"
                  placeholder={action === "REJECT" ? "Lý do từ chối..." : "Lý do yêu cầu nguồn..."}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  style={{ minWidth: 260 }}
                />
              )}
            </div>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={!canSubmit}>
              {submitting ? "Đang áp dụng..." : "Áp dụng đồng loạt"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function QualityExceptionsPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadDatasets() {
    try {
      setDatasets(await listDatasets({}));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadQueue() {
    setLoading(true);
    try {
      const data = await listQualityExceptions({
        datasetId: selectedDatasetId ? Number(selectedDatasetId) : null,
        status: statusFilter === "ALL" ? null : statusFilter,
      });
      setItems(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    loadQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId, statusFilter]);

  function handleResolved(item) {
    setInfo(`Đã lưu quyết định xử lý cho ngoại lệ #${item.id}.`);
    loadQueue();
  }

  function handleBatchResolved(result) {
    setInfo(`Đã áp dụng đồng loạt cho ${result.resolved_count} ngoại lệ cùng loại.`);
    loadQueue();
  }

  const pendingRuleTypes = useMemo(() => {
    if (!selectedDatasetId) return [];
    const seen = [];
    for (const it of items) {
      if (it.status !== "PENDING") continue;
      for (const f of it.failed_rules || []) {
        if (f.rule_type && !seen.includes(f.rule_type)) seen.push(f.rule_type);
      }
    }
    return seen;
  }, [items, selectedDatasetId]);

  return (
    <AppLayout
      title="Xử lý ngoại lệ chất lượng"
      subtitle="UC-040 — Xem hàng đợi ngoại lệ do UC-039 đẩy vào (dưới ngưỡng chất lượng); xử lý từng dòng (sửa giá trị / từ chối / yêu cầu nguồn gửi lại), hệ thống lưu quyết định; có thể xử lý hàng loạt các dòng cùng loại quy tắc không đạt."
    >
      {error && (
        <div className="alert alert-error">
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

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bước 1 — Xem hàng đợi ngoại lệ</h2>
          <button className="icon-btn" title="Làm mới" onClick={loadQueue}>
            <RefreshCw size={15} />
          </button>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="field">
              <label htmlFor="dataset-filter">Tập dữ liệu</label>
              <select
                id="dataset-filter"
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
              >
                <option value="">-- Tất cả tập dữ liệu --</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="status-filter">Trạng thái</label>
              <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="PENDING">Chưa xử lý</option>
                <option value="RESOLVED">Đã xử lý</option>
                <option value="ALL">Tất cả</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <BatchResolveCard
        datasetId={selectedDatasetId ? Number(selectedDatasetId) : null}
        ruleTypeOptions={pendingRuleTypes}
        onResolved={handleBatchResolved}
        onError={setError}
      />

      <div className="card">
        <div className="card-header">
          <h2>
            <Inbox size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Hàng đợi ngoại lệ ({items.length})
          </h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">Không có ngoại lệ nào phù hợp bộ lọc.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tập dữ liệu</th>
                  <th>Dòng</th>
                  <th>Quy tắc không đạt</th>
                  <th>Trạng thái</th>
                  <th>Kết quả xử lý</th>
                  <th>Tạo lúc</th>
                  <th style={{ minWidth: 300 }}>Xử lý (bước 2)</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.id}</td>
                    <td>{it.dataset_id}</td>
                    <td>{it.row_index}</td>
                    <td>
                      <span title={failedRuleSummary(it)}>
                        <AlertTriangle
                          size={14}
                          style={{ color: "var(--color-warning, #d97706)", verticalAlign: "middle" }}
                        />{" "}
                        {(it.failed_rules || [])
                          .map((f) => RULE_TYPE_LABEL[f.rule_type] || f.rule_type)
                          .join(", ")}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[it.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[it.status] || it.status}
                      </span>
                    </td>
                    <td>
                      {it.status === "RESOLVED" ? (
                        it.resolution_action === "FIX" ? (
                          <span>
                            <CheckCircle2
                              size={14}
                              style={{ color: "var(--color-success)", verticalAlign: "middle" }}
                            />{" "}
                            {ACTION_LABEL[it.resolution_action]}:{" "}
                            {Object.entries(it.corrected_fields || {})
                              .map(([k, v]) => `${k}=${v}`)
                              .join(", ")}
                          </span>
                        ) : (
                          <span title={it.resolution_reason}>
                            <XCircle
                              size={14}
                              style={{ color: "var(--color-danger)", verticalAlign: "middle" }}
                            />{" "}
                            {ACTION_LABEL[it.resolution_action]}
                          </span>
                        )
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{formatTime(it.created_at)}</td>
                    <td>
                      {it.status === "PENDING" ? (
                        <ResolveForm item={it} onResolved={handleResolved} onError={setError} />
                      ) : (
                        <span style={{ color: "var(--color-text-secondary, #888)" }}>
                          Đã xử lý lúc {formatTime(it.resolved_at)}
                        </span>
                      )}
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