import { useEffect, useState } from "react";
import { AlertCircle, History, Inbox, PlayCircle, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import { listMappingJobs } from "../../api/mappingJobs.js";
import {
  getQualityCheck,
  listQualityCheckExceptionItems,
  listQualityCheckPublishedRecords,
  listQualityCheckRuleResults,
  listQualityChecks,
  listQualityExceptionQueue,
  runQualityCheck,
} from "../../api/qualityChecks.js";

const STATUS_BADGE = {
  RUNNING: "badge-warning",
  PASSED: "badge-success",
  BELOW_THRESHOLD: "badge-danger",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  RUNNING: "Đang chạy",
  PASSED: "Đạt ngưỡng — đã công bố",
  BELOW_THRESHOLD: "Dưới ngưỡng — hàng đợi ngoại lệ",
  FAILED: "Thất bại",
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

function formatScore(value) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(2)}%`;
}

export default function QualityChecksPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [mappingJobs, setMappingJobs] = useState([]);
  const [selectedMappingJobId, setSelectedMappingJobId] = useState("");
  const [checks, setChecks] = useState([]);
  const [exceptionQueue, setExceptionQueue] = useState([]);

  const [lastCheck, setLastCheck] = useState(null);
  const [lastCheckDetail, setLastCheckDetail] = useState({
    ruleResults: [],
    published: [],
    exceptions: [],
  });

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

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

  async function loadMappingJobs(datasetId) {
    try {
      setMappingJobs(await listMappingJobs({ datasetId, status: "COMPLETED" }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadChecks(datasetId) {
    try {
      setChecks(await listQualityChecks({ datasetId }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadExceptionQueue(datasetId) {
    try {
      setExceptionQueue(await listQualityExceptionQueue({ datasetId, status: "PENDING" }));
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
      loadMappingJobs(id);
      loadChecks(id);
      loadExceptionQueue(id);
    } else {
      setMappingJobs([]);
      setChecks([]);
      setExceptionQueue([]);
    }
    setSelectedMappingJobId("");
    setLastCheck(null);
    setLastCheckDetail({ ruleResults: [], published: [], exceptions: [] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  const selectedDataset = datasets.find((d) => d.id === Number(selectedDatasetId));

  async function loadDetail(checkId) {
    const [ruleResults, published, exceptions] = await Promise.all([
      listQualityCheckRuleResults(checkId),
      listQualityCheckPublishedRecords(checkId),
      listQualityCheckExceptionItems(checkId),
    ]);
    setLastCheckDetail({ ruleResults, published, exceptions });
  }

  async function handleTrigger() {
    if (!selectedMappingJobId) return;
    setRunning(true);
    try {
      const check = await runQualityCheck({
        mappingJobId: Number(selectedMappingJobId),
        datasetId: selectedDataset ? selectedDataset.id : null,
      });
      setLastCheck(check);
      await loadDetail(check.id);
      if (selectedDataset) {
        await loadChecks(selectedDataset.id);
        await loadExceptionQueue(selectedDataset.id);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleViewCheck(id) {
    try {
      const check = await getQualityCheck(id);
      setLastCheck(check);
      await loadDetail(id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Chạy kiểm tra chất lượng dữ liệu"
      subtitle="UC-039 — Nhận sự kiện mapping.completed: tra cứu quy tắc chất lượng (UC-038) + chạy từng quy tắc để tính điểm; đạt ngưỡng thì công bố vào kho chuẩn hoá, dưới ngưỡng thì đẩy các dòng vi phạm vào hàng đợi ngoại lệ cho Phụ trách Dữ liệu (UC-040)."
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
            <h2>Mô phỏng sự kiện mapping.completed (kích hoạt thủ công)</h2>
          </div>
          <div className="card-body">
            {mappingJobs.length === 0 ? (
              <div className="empty-state">
                Chưa có phiên ánh xạ nào ở trạng thái "Hoàn tất" (UC-031) cho tập dữ liệu này.
              </div>
            ) : (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="mapping-job">Phiên ánh xạ (UC-031) nguồn</label>
                  <select
                    id="mapping-job"
                    value={selectedMappingJobId}
                    onChange={(e) => setSelectedMappingJobId(e.target.value)}
                  >
                    <option value="" disabled>
                      -- Chọn phiên ánh xạ --
                    </option>
                    {mappingJobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        #{j.id} — {j.records_mapped} bản ghi chuẩn hoá ({formatTime(j.completed_at)})
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleTrigger}
                  disabled={running || !selectedMappingJobId}
                >
                  <PlayCircle size={15} />
                  {running ? "Đang kiểm tra..." : "Gửi sự kiện mapping.completed"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {lastCheck && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả lượt kiểm tra #{lastCheck.id}</h2>
            <span className={`badge ${STATUS_BADGE[lastCheck.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastCheck.status] || lastCheck.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Ngưỡng đạt <strong>{lastCheck.pass_threshold}</strong>, điểm chất lượng tổng hợp{" "}
              <strong>{formatScore(lastCheck.overall_score)}</strong>, kiểm tra{" "}
              <strong>{lastCheck.records_checked}</strong> bản ghi.
              {" "}Công bố vào kho chuẩn hoá <strong>{lastCheck.published_count}</strong> bản ghi,
              đẩy hàng đợi ngoại lệ <strong>{lastCheck.exception_count}</strong> dòng.
            </p>
            {lastCheck.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastCheck.error_message}</p>
            )}

            {Object.keys(lastCheck.rule_type_scores || {}).length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Điểm theo nhóm loại quy tắc:</strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Loại quy tắc</th>
                      <th>Điểm (pass_rate trọng số)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(lastCheck.rule_type_scores).map(([type, score]) => (
                      <tr key={type}>
                        <td>{RULE_TYPE_LABEL[type] || type}</td>
                        <td>{formatScore(score)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {lastCheckDetail.ruleResults.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Bước 2 — Kết quả từng quy tắc đã chạy ({lastCheckDetail.ruleResults.length}):</strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Loại quy tắc</th>
                      <th>Trường áp dụng</th>
                      <th>Đã kiểm tra</th>
                      <th>Không đạt</th>
                      <th>Tỉ lệ đạt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastCheckDetail.ruleResults.map((r) => (
                      <tr key={r.id}>
                        <td>{RULE_TYPE_LABEL[r.rule_type] || r.rule_type}</td>
                        <td>{r.field_names.join(", ")}</td>
                        <td>{r.total_checked}</td>
                        <td>{r.failed_count}</td>
                        <td>{formatScore(r.pass_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {lastCheck.status === "PASSED" && lastCheckDetail.published.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>
                  Bước 3a — Bản ghi đã công bố vào kho chuẩn hoá ({lastCheckDetail.published.length}):
                </strong>
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
                  {JSON.stringify(lastCheckDetail.published, null, 2)}
                </pre>
              </div>
            )}

            {lastCheck.status === "BELOW_THRESHOLD" && lastCheckDetail.exceptions.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>
                  Bước 3b — Dòng đẩy vào hàng đợi ngoại lệ cho Phụ trách Dữ liệu (
                  {lastCheckDetail.exceptions.length}):
                </strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dòng</th>
                      <th>Trạng thái</th>
                      <th>Quy tắc không đạt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastCheckDetail.exceptions.map((it) => (
                      <tr key={it.id}>
                        <td>{it.row_index}</td>
                        <td>
                          <span className="badge badge-warning">{it.status}</span>
                        </td>
                        <td>
                          {it.failed_rules
                            .map((f) => `${RULE_TYPE_LABEL[f.rule_type] || f.rule_type}: ${f.reason}`)
                            .join("; ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedDataset && exceptionQueue.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>
              <Inbox size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Hàng đợi ngoại lệ đang chờ xử lý (toàn bộ tập dữ liệu, UC-040 xử lý tiếp)
            </h2>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lượt kiểm tra</th>
                  <th>Dòng</th>
                  <th>Tạo lúc</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {exceptionQueue.map((it) => (
                  <tr key={it.id}>
                    <td>#{it.quality_check_job_id}</td>
                    <td>{it.row_index}</td>
                    <td>{formatTime(it.created_at)}</td>
                    <td>
                      <span className="badge badge-warning">{it.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedDataset && (
        <div className="card">
          <div className="card-header">
            <h2>
              <History size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Lịch sử lượt kiểm tra chất lượng của tập dữ liệu này
            </h2>
            <button
              className="icon-btn"
              title="Làm mới"
              onClick={() => loadChecks(Number(selectedDatasetId))}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {checks.length === 0 ? (
              <div className="empty-state">Chưa có lượt kiểm tra chất lượng nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nhận lúc</th>
                    <th>Kết thúc</th>
                    <th>Trạng thái</th>
                    <th>Điểm</th>
                    <th>Công bố / Ngoại lệ</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {checks.map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{formatTime(c.received_at)}</td>
                      <td>{formatTime(c.completed_at)}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[c.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[c.status] || c.status}
                        </span>
                      </td>
                      <td>{formatScore(c.overall_score)}</td>
                      <td>
                        {c.published_count}/{c.exception_count}
                      </td>
                      <td>
                        <button className="icon-btn" title="Xem chi tiết" onClick={() => handleViewCheck(c.id)}>
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