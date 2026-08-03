import { useEffect, useState } from "react";
import { AlertCircle, History, PlayCircle, Plus, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import { listParsingJobs } from "../../api/parsingJobs.js";
import {
  createMappingRule,
  getMappingJob,
  listMappedStandardRecords,
  listMappingJobs,
  listMappingRejections,
  listMappingRules,
  listUnmappedQueue,
  receiveMappingRequested,
} from "../../api/mappingJobs.js";

const STATUS_BADGE = {
  RECEIVED: "badge-neutral",
  RUNNING: "badge-warning",
  COMPLETED: "badge-success",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  RECEIVED: "Đã nhận",
  RUNNING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
};

const RULE_TYPES = ["DIRECT", "CATALOG_LOOKUP"];
const NORMALIZE_CASES = ["", "UPPER", "LOWER"];

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function MappingJobsPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [parsingJobs, setParsingJobs] = useState([]);
  const [selectedParsingJobId, setSelectedParsingJobId] = useState("");
  const [jobs, setJobs] = useState([]);
  const [lastJob, setLastJob] = useState(null);
  const [lastJobDetail, setLastJobDetail] = useState({ rejections: [], queue: [], records: [] });
  const [rules, setRules] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  // Form đăng ký quy tắc ánh xạ.
  const [ruleFieldName, setRuleFieldName] = useState("");
  const [ruleType, setRuleType] = useState("DIRECT");
  const [ruleVersion, setRuleVersion] = useState(1);
  const [ruleCatalogMap, setRuleCatalogMap] = useState("{}");
  const [ruleNormalizeCase, setRuleNormalizeCase] = useState("");
  const [creatingRule, setCreatingRule] = useState(false);

  async function loadDatasets() {
    setLoading(true);
    try {
      setDatasets(await listDatasets({}));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadParsingJobs(datasetId) {
    try {
      setParsingJobs(await listParsingJobs({ datasetId, status: "MAPPED" }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadMappingJobs(datasetId) {
    try {
      setJobs(await listMappingJobs({ datasetId }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadRules(datasetId) {
    try {
      setRules(await listMappingRules({ datasetId }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    if (selectedDatasetId) {
      const id = Number(selectedDatasetId);
      loadParsingJobs(id);
      loadMappingJobs(id);
      loadRules(id);
    } else {
      setParsingJobs([]);
      setJobs([]);
      setRules([]);
    }
    setSelectedParsingJobId("");
    setLastJob(null);
    setLastJobDetail({ rejections: [], queue: [], records: [] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  const selectedDataset = datasets.find((d) => d.id === Number(selectedDatasetId));

  async function handleCreateRule() {
    if (!ruleFieldName.trim()) return;
    setCreatingRule(true);
    try {
      let catalogMap = {};
      if (ruleType === "CATALOG_LOOKUP") {
        catalogMap = JSON.parse(ruleCatalogMap || "{}");
      }
      await createMappingRule({
        fieldName: ruleFieldName.trim(),
        version: Number(ruleVersion) || 1,
        ruleType,
        datasetId: selectedDataset ? selectedDataset.id : null,
        catalogMap,
        normalizeCase: ruleNormalizeCase || null,
      });
      setRuleFieldName("");
      setRuleCatalogMap("{}");
      if (selectedDataset) await loadRules(selectedDataset.id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setCreatingRule(false);
    }
  }

  async function loadDetail(jobId) {
    const [rejections, queue, records] = await Promise.all([
      listMappingRejections(jobId),
      listUnmappedQueue(jobId),
      listMappedStandardRecords(jobId),
    ]);
    setLastJobDetail({ rejections, queue, records });
  }

  async function handleTrigger() {
    if (!selectedParsingJobId) return;
    setRunning(true);
    try {
      const job = await receiveMappingRequested({ parsingJobId: Number(selectedParsingJobId) });
      setLastJob(job);
      await loadDetail(job.id);
      if (selectedDataset) await loadMappingJobs(selectedDataset.id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleViewJob(id) {
    try {
      const job = await getMappingJob(id);
      setLastJob(job);
      await loadDetail(id);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Ánh xạ trường sang dạng chuẩn"
      subtitle="UC-031 — Nhận sự kiện mapping.requested: tra cứu quy tắc ánh xạ (có phiên bản) + tra cứu danh mục chuẩn, chuẩn hoá field, từ chối trường bắt buộc bị NULL, đẩy giá trị chưa ánh xạ vào hàng đợi cho Phụ trách Dữ liệu."
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
            <div className="empty-state">Chưa có tập dữ liệu nào (UC-018).</div>
          ) : (
            <div className="field">
              <label htmlFor="dataset">Tập dữ liệu</label>
              <select
                id="dataset"
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
              >
                <option value="" disabled>
                  -- Chọn tập dữ liệu --
                </option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {selectedDataset && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Bước 1 — Đăng ký quy tắc ánh xạ (có phiên bản)</h2>
          </div>
          <div className="card-body">
            <div className="form-grid">
              <div className="field">
                <label htmlFor="rule-field-name">Tên trường</label>
                <input
                  id="rule-field-name"
                  type="text"
                  placeholder="vd: loai_don_vi"
                  value={ruleFieldName}
                  onChange={(e) => setRuleFieldName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="rule-type">Loại quy tắc</label>
                <select id="rule-type" value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                  {RULE_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="rule-version">Phiên bản</label>
                <input
                  id="rule-version"
                  type="number"
                  min={1}
                  value={ruleVersion}
                  onChange={(e) => setRuleVersion(e.target.value)}
                />
              </div>
              {ruleType === "DIRECT" ? (
                <div className="field">
                  <label htmlFor="rule-normalize-case">Chuẩn hoá hoa/thường</label>
                  <select
                    id="rule-normalize-case"
                    value={ruleNormalizeCase}
                    onChange={(e) => setRuleNormalizeCase(e.target.value)}
                  >
                    {NORMALIZE_CASES.map((c) => (
                      <option key={c} value={c}>
                        {c || "(không đổi)"}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="rule-catalog-map">
                    Danh mục chuẩn (JSON: giá trị nguồn viết HOA -&gt; giá trị chuẩn)
                  </label>
                  <input
                    id="rule-catalog-map"
                    type="text"
                    placeholder='vd: {"SO": "Sở", "PHONG": "Phòng"}'
                    value={ruleCatalogMap}
                    onChange={(e) => setRuleCatalogMap(e.target.value)}
                  />
                </div>
              )}
              <button
                className="btn btn-secondary"
                onClick={handleCreateRule}
                disabled={creatingRule || !ruleFieldName.trim()}
              >
                <Plus size={15} />
                {creatingRule ? "Đang lưu..." : "Đăng ký quy tắc"}
              </button>
            </div>

            {rules.length > 0 && (
              <table className="data-table" style={{ marginTop: 14 }}>
                <thead>
                  <tr>
                    <th>Trường</th>
                    <th>Phiên bản</th>
                    <th>Loại</th>
                    <th>Đang áp dụng</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id}>
                      <td>{r.field_name}</td>
                      <td>{r.version}</td>
                      <td>{r.rule_type}</td>
                      <td>{r.is_active ? "Có" : "Không"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {selectedDataset && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Mô phỏng sự kiện mapping.requested (kích hoạt thủ công)</h2>
          </div>
          <div className="card-body">
            {parsingJobs.length === 0 ? (
              <div className="empty-state">
                Chưa có phiên phân tích nào ở trạng thái "Đã ánh xạ" (UC-029) cho tập dữ liệu này.
              </div>
            ) : (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="parsing-job">Phiên phân tích (UC-029) nguồn</label>
                  <select
                    id="parsing-job"
                    value={selectedParsingJobId}
                    onChange={(e) => setSelectedParsingJobId(e.target.value)}
                  >
                    <option value="" disabled>
                      -- Chọn phiên phân tích --
                    </option>
                    {parsingJobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        #{j.id} — {j.records_parsed} bản ghi ({formatTime(j.received_at)})
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleTrigger}
                  disabled={running || !selectedParsingJobId}
                >
                  <PlayCircle size={15} />
                  {running ? "Đang xử lý..." : "Gửi sự kiện mapping.requested"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {lastJob && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả phiên ánh xạ #{lastJob.id}</h2>
            <span className={`badge ${STATUS_BADGE[lastJob.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastJob.status] || lastJob.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Tổng <strong>{lastJob.records_total}</strong> dòng, ánh xạ chuẩn hoá thành công{" "}
              <strong>{lastJob.records_mapped}</strong>, từ chối{" "}
              <strong>{lastJob.records_rejected}</strong> (trường bắt buộc bị NULL), giá trị chưa
              ánh xạ đẩy vào hàng đợi <strong>{lastJob.unmapped_values_count}</strong>.
            </p>
            {lastJob.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastJob.error_message}</p>
            )}

            {lastJobDetail.rejections.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Bước 2 — Dòng bị từ chối ({lastJobDetail.rejections.length}):</strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dòng</th>
                      <th>Trường bắt buộc</th>
                      <th>Lý do</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastJobDetail.rejections.map((r, i) => (
                      <tr key={i}>
                        <td>{r.row_index}</td>
                        <td>{r.field_name}</td>
                        <td>{r.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {lastJobDetail.queue.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>
                  Bước 3 — Hàng đợi giá trị chưa ánh xạ cho Phụ trách Dữ liệu (
                  {lastJobDetail.queue.length}):
                </strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dòng</th>
                      <th>Trường</th>
                      <th>Giá trị nguồn</th>
                      <th>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastJobDetail.queue.map((it, i) => (
                      <tr key={i}>
                        <td>{it.row_index}</td>
                        <td>{it.field_name}</td>
                        <td>{it.raw_value}</td>
                        <td>{it.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {lastJobDetail.records.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Bản ghi đã ánh xạ chuẩn hoá ({lastJobDetail.records.length}):</strong>
                <pre
                  style={{
                    background: "var(--color-bg-secondary, #f5f5f5)",
                    padding: 10,
                    borderRadius: 6,
                    fontSize: 12,
                    whiteSpace: "pre-wrap",
                    maxHeight: 240,
                    overflow: "auto",
                  }}
                >
                  {JSON.stringify(lastJobDetail.records, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedDataset && (
        <div className="card">
          <div className="card-header">
            <h2>
              <History size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Lịch sử phiên ánh xạ của tập dữ liệu này
            </h2>
            <button
              className="icon-btn"
              title="Làm mới"
              onClick={() => loadMappingJobs(Number(selectedDatasetId))}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {jobs.length === 0 ? (
              <div className="empty-state">Chưa có phiên ánh xạ nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nhận lúc</th>
                    <th>Kết thúc</th>
                    <th>Trạng thái</th>
                    <th>Số bản ghi</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id}>
                      <td>{j.id}</td>
                      <td>{formatTime(j.received_at)}</td>
                      <td>{formatTime(j.completed_at)}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[j.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[j.status] || j.status}
                        </span>
                      </td>
                      <td>
                        {j.records_mapped}/{j.records_total}
                      </td>
                      <td>
                        <button className="icon-btn" title="Xem chi tiết" onClick={() => handleViewJob(j.id)}>
                          Xem
                        </button>
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