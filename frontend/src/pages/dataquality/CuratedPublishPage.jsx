import { useEffect, useState } from "react";
import { AlertCircle, Database, History, PlayCircle, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import { listQualityChecks } from "../../api/qualityChecks.js";
import {
  getCuratedPublishJob,
  getDatasetFreshness,
  listBatchSummaries,
  listCuratedPublishJobDmRecords,
  listCuratedPublishJobs,
  listDmRecords,
  runCuratedPublish,
} from "../../api/curatedPublish.js";

const STATUS_BADGE = {
  RUNNING: "badge-warning",
  COMPLETED: "badge-success",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  RUNNING: "Đang công bố",
  COMPLETED: "Đã công bố",
  FAILED: "Thất bại",
};

const SOURCE_LABEL = {
  uc039_quality_check: "UC-039 — Đạt ngưỡng chất lượng",
  uc040_exception_fix: "UC-040 — Sửa ngoại lệ (FIX)",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function CuratedPublishPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [passedChecks, setPassedChecks] = useState([]);
  const [selectedCheckId, setSelectedCheckId] = useState("");
  const [jobs, setJobs] = useState([]);
  const [freshness, setFreshness] = useState(null);

  const [lastJob, setLastJob] = useState(null);
  const [lastJobDmRecords, setLastJobDmRecords] = useState([]);
  const [lastJobSummaries, setLastJobSummaries] = useState([]);

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

  async function loadPassedChecks(datasetId) {
    try {
      const checks = await listQualityChecks({ datasetId, status: "PASSED" });
      setPassedChecks(checks);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadJobs(datasetId) {
    try {
      setJobs(await listCuratedPublishJobs({ datasetId }));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function loadFreshness(datasetId) {
    try {
      setFreshness(await getDatasetFreshness(datasetId));
    } catch {
      setFreshness(null);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    if (selectedDatasetId) {
      const id = Number(selectedDatasetId);
      loadPassedChecks(id);
      loadJobs(id);
      loadFreshness(id);
    } else {
      setPassedChecks([]);
      setJobs([]);
      setFreshness(null);
    }
    setSelectedCheckId("");
    setLastJob(null);
    setLastJobDmRecords([]);
    setLastJobSummaries([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  const selectedDataset = datasets.find((d) => d.id === Number(selectedDatasetId));

  async function loadDetail(jobId, datasetId) {
    const [dmRecords, summaries] = await Promise.all([
      listCuratedPublishJobDmRecords(jobId),
      listBatchSummaries({ datasetId }),
    ]);
    setLastJobDmRecords(dmRecords);
    setLastJobSummaries(summaries);
  }

  async function handleTrigger() {
    if (!selectedCheckId) return;
    setRunning(true);
    try {
      const job = await runCuratedPublish({
        qualityCheckJobId: Number(selectedCheckId),
        datasetId: selectedDataset ? selectedDataset.id : null,
      });
      setLastJob(job);
      await loadDetail(job.id, selectedDataset ? selectedDataset.id : null);
      if (selectedDataset) {
        await loadJobs(selectedDataset.id);
        await loadFreshness(selectedDataset.id);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleViewJob(id) {
    try {
      const job = await getCuratedPublishJob(id);
      setLastJob(job);
      await loadDetail(id, job.dataset_id);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Công bố vào kho chuẩn hoá + batch_summary"
      subtitle="UC-041 — Nhận sự kiện curated.publish.requested (UC-039 đạt ngưỡng chất lượng, hoặc UC-040 khi sửa 1 ngoại lệ): chèn/cập nhật vào dm_*, đặt publish_status=approved, tạo batch_summary + cập nhật độ mới dữ liệu, phát sự kiện curated.published."
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

      {selectedDataset && freshness && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>
              <Database size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Độ mới dữ liệu kho chuẩn hoá
            </h2>
          </div>
          <div className="card-body">
            <p>
              Công bố gần nhất lúc <strong>{formatTime(freshness.last_published_at)}</strong>, tổng{" "}
              <strong>{freshness.total_published_records}</strong> bản ghi đã công bố (batch_summary
              gần nhất #{freshness.last_batch_summary_id}).
            </p>
          </div>
        </div>
      )}

      {selectedDataset && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Mô phỏng sự kiện curated.publish.requested (kích hoạt thủ công)</h2>
          </div>
          <div className="card-body">
            {passedChecks.length === 0 ? (
              <div className="empty-state">
                Chưa có lượt kiểm tra chất lượng nào ở trạng thái "Đạt ngưỡng" (UC-039) cho tập dữ liệu
                này.
              </div>
            ) : (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="quality-check">Lượt kiểm tra chất lượng (UC-039) nguồn</label>
                  <select
                    id="quality-check"
                    value={selectedCheckId}
                    onChange={(e) => setSelectedCheckId(e.target.value)}
                  >
                    <option value="" disabled>
                      -- Chọn lượt kiểm tra --
                    </option>
                    {passedChecks.map((c) => (
                      <option key={c.id} value={c.id}>
                        #{c.id} — {c.published_count} bản ghi ({formatTime(c.completed_at)})
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleTrigger}
                  disabled={running || !selectedCheckId}
                >
                  <PlayCircle size={15} />
                  {running ? "Đang công bố..." : "Gửi sự kiện curated.publish.requested"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {lastJob && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h2>Kết quả lượt công bố #{lastJob.id}</h2>
            <span className={`badge ${STATUS_BADGE[lastJob.status] || "badge-neutral"}`}>
              {STATUS_LABEL[lastJob.status] || lastJob.status}
            </span>
          </div>
          <div className="card-body">
            <p>
              Nguồn <strong>{SOURCE_LABEL[lastJob.source] || lastJob.source}</strong>, nhận{" "}
              <strong>{lastJob.records_received}</strong> bản ghi -- bước 1 chèn mới{" "}
              <strong>{lastJob.inserted_count}</strong>, cập nhật <strong>{lastJob.updated_count}</strong>{" "}
              bản ghi vào <code>dm_*</code>. Đã phát sự kiện curated.published:{" "}
              <strong>{lastJob.published_event_published ? "Có" : "Không"}</strong>.
            </p>
            {lastJob.error_message && (
              <p style={{ color: "var(--color-danger)" }}>Lỗi: {lastJob.error_message}</p>
            )}

            {lastJobDmRecords.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>
                  Bước 1+2 — Bản ghi đã chèn/cập nhật vào dm_* (publish_status=approved) (
                  {lastJobDmRecords.length}):
                </strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dòng</th>
                      <th>Phiên bản</th>
                      <th>Trạng thái công bố</th>
                      <th>Cập nhật lúc</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastJobDmRecords.map((r) => (
                      <tr key={r.id}>
                        <td>{r.row_index}</td>
                        <td>{r.version}</td>
                        <td>
                          <span className="badge badge-success">{r.publish_status}</span>
                        </td>
                        <td>{formatTime(r.last_published_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {lastJobSummaries.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <strong>Bước 3 — batch_summary của tập dữ liệu này ({lastJobSummaries.length}):</strong>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nguồn</th>
                      <th>Nhận</th>
                      <th>Chèn mới</th>
                      <th>Cập nhật</th>
                      <th>Tạo lúc</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastJobSummaries.map((s) => (
                      <tr key={s.id}>
                        <td>{s.id}</td>
                        <td>{SOURCE_LABEL[s.source] || s.source}</td>
                        <td>{s.records_received}</td>
                        <td>{s.inserted_count}</td>
                        <td>{s.updated_count}</td>
                        <td>{formatTime(s.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
              Lịch sử lượt công bố vào kho chuẩn hoá của tập dữ liệu này
            </h2>
            <button
              className="icon-btn"
              title="Làm mới"
              onClick={() => loadJobs(Number(selectedDatasetId))}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {jobs.length === 0 ? (
              <div className="empty-state">Chưa có lượt công bố nào cho tập dữ liệu này.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nhận lúc</th>
                    <th>Kết thúc</th>
                    <th>Trạng thái</th>
                    <th>Chèn mới / Cập nhật</th>
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
                        {j.inserted_count}/{j.updated_count}
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