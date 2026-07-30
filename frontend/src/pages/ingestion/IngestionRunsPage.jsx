import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CalendarDays, History, X } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import { getDataCalendar, getRunDetail, listRunHistory } from "../../api/ingestionRuns.js";

const STATUS_BADGE = {
  RUNNING: "badge-warning",
  SUCCESS: "badge-success",
  FAILED: "badge-danger",
  PARTIAL: "badge-neutral",
};

const STATUS_LABEL = {
  RUNNING: "Đang chạy",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
  PARTIAL: "Một phần",
};

const TRIGGER_LABEL = {
  MANUAL: "Thủ công",
  SCHEDULED: "Tự động (điều phối)",
  RETRY: "Chạy lại",
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function heatColor(day) {
  if (day.run_count === 0) return "var(--color-danger-soft, #fde2e2)";
  if (day.success_count > 0 && day.failed_count === 0) return "var(--color-success-soft, #d9f4e3)";
  if (day.success_count > 0 && day.failed_count > 0) return "#fff2cc";
  return "var(--color-danger-soft, #fde2e2)";
}

function heatTextColor(day) {
  if (day.run_count === 0) return "#a83232";
  if (day.success_count > 0 && day.failed_count === 0) return "#1f7a45";
  if (day.success_count > 0 && day.failed_count > 0) return "#8a6d00";
  return "#a83232";
}

export default function IngestionRunsPage() {
  const [tab, setTab] = useState("history"); // history | calendar
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // ---- Lịch sử chạy ----
  const [runs, setRuns] = useState([]);
  const [filterDataset, setFilterDataset] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  // ---- Lịch đầy đủ dữ liệu (heatmap) ----
  const [calendarDataset, setCalendarDataset] = useState("");
  const [calendarFrom, setCalendarFrom] = useState(daysAgoISO(29));
  const [calendarTo, setCalendarTo] = useState(todayISO());
  const [calendarDays, setCalendarDays] = useState([]);

  // ---- Chi tiết phiên ----
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  async function loadDatasets() {
    try {
      const data = await listDatasets({});
      setDatasets(data);
      if (data.length > 0) setCalendarDataset(String(data[0].id));
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function reloadHistory() {
    setLoading(true);
    try {
      const data = await listRunHistory({
        datasetId: filterDataset || null,
        status: filterStatus || null,
        dateFrom: filterDateFrom || null,
        dateTo: filterDateTo || null,
      });
      setRuns(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function reloadCalendar() {
    if (!calendarDataset) return;
    setLoading(true);
    try {
      const data = await getDataCalendar({
        datasetId: Number(calendarDataset),
        dateFrom: calendarFrom,
        dateTo: calendarTo,
      });
      setCalendarDays(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDatasets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === "history") reloadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, filterDataset, filterStatus, filterDateFrom, filterDateTo]);

  useEffect(() => {
    if (tab === "calendar") reloadCalendar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, calendarDataset, calendarFrom, calendarTo]);

  function datasetLabel(id) {
    const ds = datasets.find((d) => d.id === id);
    return ds ? `${ds.code} — ${ds.name}` : `#${id}`;
  }

  async function openDetail(runId) {
    setDetailLoading(true);
    try {
      const data = await getRunDetail(runId);
      setDetail(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  const missingCount = useMemo(
    () => calendarDays.filter((d) => d.is_missing).length,
    [calendarDays]
  );

  return (
    <AppLayout
      title="Lịch đầy đủ dữ liệu + Lịch sử chạy"
      subtitle="UC-020 — Xem lịch sử các phiên ingest, heatmap kỳ thiếu dữ liệu và chi tiết log + tổng kiểm soát của từng phiên."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          className={`btn ${tab === "history" ? "btn-primary" : ""}`}
          onClick={() => setTab("history")}
        >
          <History size={15} />
          Lịch sử chạy
        </button>
        <button
          className={`btn ${tab === "calendar" ? "btn-primary" : ""}`}
          onClick={() => setTab("calendar")}
        >
          <CalendarDays size={15} />
          Lịch đầy đủ dữ liệu
        </button>
      </div>

      {tab === "history" && (
        <div className="card">
          <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
            <h2>Danh sách phiên đã chạy ({runs.length})</h2>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={filterDataset}
                onChange={(e) => setFilterDataset(e.target.value)}
                style={{ width: "auto" }}
              >
                <option value="">Tất cả tập dữ liệu</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                style={{ width: "auto" }}
              >
                <option value="">Tất cả trạng thái</option>
                <option value="RUNNING">Đang chạy</option>
                <option value="SUCCESS">Thành công</option>
                <option value="FAILED">Thất bại</option>
                <option value="PARTIAL">Một phần</option>
              </select>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                style={{ width: "auto" }}
                title="Từ ngày"
              />
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                style={{ width: "auto" }}
                title="Đến ngày"
              />
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {loading ? (
              <div className="empty-state">Đang tải dữ liệu...</div>
            ) : runs.length === 0 ? (
              <div className="empty-state">Chưa có phiên ingest nào khớp bộ lọc.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Tập dữ liệu</th>
                    <th>Kích hoạt</th>
                    <th>Bắt đầu</th>
                    <th>Kết thúc</th>
                    <th>Đọc / Nạp / Lỗi</th>
                    <th>Trạng thái</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}</td>
                      <td>{datasetLabel(r.dataset_id)}</td>
                      <td>{TRIGGER_LABEL[r.trigger] || r.trigger}</td>
                      <td>{r.started_at}</td>
                      <td>{r.finished_at || "—"}</td>
                      <td>
                        {r.records_read} / {r.records_loaded} / {r.records_failed}
                      </td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[r.status] || "badge-neutral"}`}>
                          {STATUS_LABEL[r.status] || r.status}
                        </span>
                        {r.error_message && (
                          <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                            {r.error_message}
                          </div>
                        )}
                      </td>
                      <td>
                        <button className="btn" onClick={() => openDetail(r.id)}>
                          Xem chi tiết
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

      {tab === "calendar" && (
        <div className="card">
          <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
            <h2>
              Lịch đầy đủ dữ liệu {missingCount > 0 && `— ${missingCount} ngày thiếu dữ liệu`}
            </h2>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={calendarDataset}
                onChange={(e) => setCalendarDataset(e.target.value)}
                style={{ width: "auto" }}
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
              <input
                type="date"
                value={calendarFrom}
                onChange={(e) => setCalendarFrom(e.target.value)}
                style={{ width: "auto" }}
                title="Từ ngày"
              />
              <input
                type="date"
                value={calendarTo}
                onChange={(e) => setCalendarTo(e.target.value)}
                style={{ width: "auto" }}
                title="Đến ngày"
              />
            </div>
          </div>
          <div className="card-body">
            {loading ? (
              <div className="empty-state">Đang tải dữ liệu...</div>
            ) : !calendarDataset ? (
              <div className="empty-state">Chọn tập dữ liệu để xem lịch đầy đủ dữ liệu.</div>
            ) : calendarDays.length === 0 ? (
              <div className="empty-state">Không có dữ liệu trong khoảng thời gian đã chọn.</div>
            ) : (
              <>
                <div style={{ display: "flex", gap: 16, marginBottom: 16, fontSize: 13 }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: 4,
                        background: "var(--color-success-soft, #d9f4e3)",
                        display: "inline-block",
                      }}
                    />
                    Đầy đủ dữ liệu (có phiên SUCCESS)
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: 4,
                        background: "#fff2cc",
                        display: "inline-block",
                      }}
                    />
                    Có SUCCESS + FAILED (một phần)
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: 4,
                        background: "var(--color-danger-soft, #fde2e2)",
                        display: "inline-block",
                      }}
                    />
                    Thiếu dữ liệu (không có phiên SUCCESS)
                  </span>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(90px, 1fr))",
                    gap: 8,
                  }}
                >
                  {calendarDays.map((d) => (
                    <div
                      key={d.date}
                      title={`${d.date}: ${d.run_count} phiên (${d.success_count} thành công, ${d.failed_count} lỗi)`}
                      style={{
                        background: heatColor(d),
                        color: heatTextColor(d),
                        borderRadius: 8,
                        padding: "10px 8px",
                        textAlign: "center",
                        cursor: d.run_count > 0 ? "pointer" : "default",
                      }}
                      onClick={() => {
                        if (d.run_count > 0) {
                          setFilterDataset(calendarDataset);
                          setFilterDateFrom(d.date);
                          setFilterDateTo(d.date);
                          setTab("history");
                        }
                      }}
                    >
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{d.date.slice(5)}</div>
                      <div style={{ fontSize: 11 }}>{d.run_count} phiên</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {(detail || detailLoading) && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
          }}
          onClick={() => setDetail(null)}
        >
          <div
            className="card"
            style={{ width: "min(720px, 92vw)", maxHeight: "85vh", overflow: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="card-header">
              <h2>Chi tiết phiên #{detail?.id}</h2>
              <button className="icon-btn" onClick={() => setDetail(null)}>
                <X size={16} />
              </button>
            </div>
            <div className="card-body">
              {detailLoading || !detail ? (
                <div className="empty-state">Đang tải...</div>
              ) : (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <div>
                      <strong>Tập dữ liệu:</strong> {datasetLabel(detail.dataset_id)}
                    </div>
                    <div>
                      <strong>Kích hoạt:</strong> {TRIGGER_LABEL[detail.trigger] || detail.trigger}{" "}
                      ({detail.sync_mode})
                    </div>
                    <div>
                      <strong>Bắt đầu:</strong> {detail.started_at}
                    </div>
                    <div>
                      <strong>Kết thúc:</strong> {detail.finished_at || "—"}
                    </div>
                    <div>
                      <strong>Trạng thái:</strong>{" "}
                      <span className={`badge ${STATUS_BADGE[detail.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[detail.status] || detail.status}
                      </span>
                    </div>
                    {detail.error_message && (
                      <div style={{ color: "var(--color-danger)" }}>
                        <strong>Lỗi:</strong> {detail.error_message}
                      </div>
                    )}
                  </div>

                  <h3 style={{ fontSize: 14, marginBottom: 8 }}>Tổng kiểm soát (control totals)</h3>
                  <table className="data-table" style={{ marginBottom: 16 }}>
                    <tbody>
                      <tr>
                        <td>Số bản ghi đọc được</td>
                        <td>{detail.records_read}</td>
                      </tr>
                      <tr>
                        <td>Số bản ghi nạp thành công</td>
                        <td>{detail.records_loaded}</td>
                      </tr>
                      <tr>
                        <td>Số bản ghi lỗi</td>
                        <td>{detail.records_failed}</td>
                      </tr>
                      {Object.entries(detail.control_totals || {}).map(([k, v]) => (
                        <tr key={k}>
                          <td>{k}</td>
                          <td>{String(v)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h3 style={{ fontSize: 14, marginBottom: 8 }}>Log ({detail.log_entries.length})</h3>
                  {detail.log_entries.length === 0 ? (
                    <div className="empty-state">Chưa có log.</div>
                  ) : (
                    <div
                      style={{
                        fontFamily: "monospace",
                        fontSize: 12,
                        background: "var(--color-bg-soft, #f4f5f7)",
                        borderRadius: 8,
                        padding: 12,
                        maxHeight: 260,
                        overflow: "auto",
                      }}
                    >
                      {detail.log_entries.map((l, i) => (
                        <div key={i} style={{ marginBottom: 4 }}>
                          <span style={{ color: "var(--color-text-secondary)" }}>
                            [{l.timestamp}]
                          </span>{" "}
                          <strong>{l.level}</strong> — {l.message}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}