import { useEffect, useState } from "react";
import { AlertCircle, Pencil, Plus, Power, PowerOff, X } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import {
  configureScheduledTask,
  disableScheduledTask,
  enableScheduledTask,
  listScheduledTasks,
  updateScheduledTaskConfig,
} from "../../api/scheduledTasks.js";

const SYNC_MODES = [
  { value: "FULL", label: "Đầy đủ (FULL)" },
  { value: "INCREMENTAL", label: "Tăng dần (INCREMENTAL)" },
];

const RETRY_BACKOFFS = [
  { value: "NONE", label: "Không thử lại" },
  { value: "FIXED", label: "Cố định" },
  { value: "EXPONENTIAL", label: "Cấp số nhân" },
];

const STATUS_BADGE = {
  IDLE: "badge-neutral",
  RUNNING: "badge-warning",
  SUCCESS: "badge-success",
  FAILED: "badge-danger",
};

const STATUS_LABEL = {
  IDLE: "Chưa chạy",
  RUNNING: "Đang chạy",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
};

const EMPTY_FORM = {
  dataset_id: "",
  code: "",
  name: "",
  sync_mode: "FULL",
  cron_expression: "0 0 * * *",
  retry_max_attempts: 3,
  retry_delay_seconds: 60,
  retry_backoff: "FIXED",
};

function syncModeLabel(value) {
  return SYNC_MODES.find((s) => s.value === value)?.label || value;
}

function retryBackoffLabel(value) {
  return RETRY_BACKOFFS.find((s) => s.value === value)?.label || value;
}

export default function ScheduledTasksPage() {
  const [tasks, setTasks] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [onlyEnabled, setOnlyEnabled] = useState(false);
  const [filterDataset, setFilterDataset] = useState("");

  async function reload() {
    setLoading(true);
    try {
      const data = await listScheduledTasks({
        onlyEnabled,
        datasetId: filterDataset || null,
      });
      setTasks(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDatasets() {
    try {
      const data = await listDatasets({});
      setDatasets(data);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadDatasets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyEnabled, filterDataset]);

  function datasetLabel(id) {
    const ds = datasets.find((d) => d.id === id);
    return ds ? `${ds.code} — ${ds.name}` : `#${id}`;
  }

  function startEdit(task) {
    setEditingId(task.id);
    setForm({
      dataset_id: task.dataset_id,
      code: task.code,
      name: task.name,
      sync_mode: task.sync_mode,
      cron_expression: task.cron_expression,
      retry_max_attempts: task.retry_max_attempts,
      retry_delay_seconds: task.retry_delay_seconds,
      retry_backoff: task.retry_backoff,
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      if (editingId) {
        await updateScheduledTaskConfig(editingId, {
          sync_mode: form.sync_mode,
          cron_expression: form.cron_expression,
          retry_max_attempts: Number(form.retry_max_attempts),
          retry_delay_seconds: Number(form.retry_delay_seconds),
          retry_backoff: form.retry_backoff,
        });
      } else {
        await configureScheduledTask({
          dataset_id: Number(form.dataset_id),
          code: form.code,
          name: form.name,
          sync_mode: form.sync_mode,
          cron_expression: form.cron_expression,
          retry_max_attempts: Number(form.retry_max_attempts),
          retry_delay_seconds: Number(form.retry_delay_seconds),
          retry_backoff: form.retry_backoff,
        });
      }
      cancelEdit();
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleToggleEnabled(task) {
    try {
      if (task.is_enabled) {
        await disableScheduledTask(task.id);
      } else {
        await enableScheduledTask(task.id);
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Cấu hình tác vụ điều phối"
      subtitle="UC-019 — Cấu hình lịch cron, chế độ đồng bộ đầy đủ/tăng dần, chính sách thử lại; bật/tắt tác vụ điều phối."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>{editingId ? "Sửa cấu hình tác vụ" : "Cấu hình tác vụ mới"}</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="dataset_id">Tập dữ liệu</label>
                <select
                  id="dataset_id"
                  value={form.dataset_id}
                  onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}
                  required
                  disabled={!!editingId}
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
              <div className="field">
                <label htmlFor="code">Mã tác vụ</label>
                <input
                  id="code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  required
                  disabled={!!editingId}
                />
              </div>
              <div className="field">
                <label htmlFor="name">Tên tác vụ</label>
                <input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  disabled={!!editingId}
                />
              </div>
              <div className="field">
                <label htmlFor="sync_mode">Chế độ đồng bộ</label>
                <select
                  id="sync_mode"
                  value={form.sync_mode}
                  onChange={(e) => setForm({ ...form, sync_mode: e.target.value })}
                >
                  {SYNC_MODES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="cron_expression">Lịch cron (5 trường)</label>
                <input
                  id="cron_expression"
                  placeholder="phút giờ ngày tháng thứ, vd: 0 2 * * *"
                  value={form.cron_expression}
                  onChange={(e) => setForm({ ...form, cron_expression: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="retry_max_attempts">Số lần thử lại tối đa</label>
                <input
                  id="retry_max_attempts"
                  type="number"
                  min="0"
                  value={form.retry_max_attempts}
                  onChange={(e) => setForm({ ...form, retry_max_attempts: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="retry_delay_seconds">Khoảng chờ thử lại (giây)</label>
                <input
                  id="retry_delay_seconds"
                  type="number"
                  min="0"
                  value={form.retry_delay_seconds}
                  onChange={(e) => setForm({ ...form, retry_delay_seconds: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="retry_backoff">Chính sách thử lại</label>
                <select
                  id="retry_backoff"
                  value={form.retry_backoff}
                  onChange={(e) => setForm({ ...form, retry_backoff: e.target.value })}
                >
                  {RETRY_BACKOFFS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary">
                  {editingId ? <Pencil size={15} /> : <Plus size={15} />}
                  {editingId ? "Lưu thay đổi" : "Cấu hình tác vụ"}
                </button>
                {editingId && (
                  <button type="button" className="btn" onClick={cancelEdit}>
                    <X size={15} />
                    Huỷ
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Danh sách tác vụ điều phối ({tasks.length})</h2>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
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
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={onlyEnabled}
                onChange={(e) => setOnlyEnabled(e.target.checked)}
              />
              Chỉ hiện đang bật
            </label>
          </div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : tasks.length === 0 ? (
            <div className="empty-state">Chưa có tác vụ điều phối nào. Cấu hình tác vụ đầu tiên ở trên.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mã</th>
                  <th>Tên tác vụ</th>
                  <th>Tập dữ liệu</th>
                  <th>Chế độ</th>
                  <th>Lịch cron</th>
                  <th>Thử lại</th>
                  <th>Trạng thái</th>
                  <th>Bật/Tắt</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.code}</td>
                    <td>{t.name}</td>
                    <td>{datasetLabel(t.dataset_id)}</td>
                    <td>{syncModeLabel(t.sync_mode)}</td>
                    <td>
                      <code>{t.cron_expression}</code>
                    </td>
                    <td>
                      tối đa {t.retry_max_attempts} lần, {t.retry_delay_seconds}s (
                      {retryBackoffLabel(t.retry_backoff)})
                    </td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[t.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[t.status] || t.status}
                      </span>
                      {t.last_run_message && (
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {t.last_run_message}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${t.is_enabled ? "badge-success" : "badge-neutral"}`}>
                        {t.is_enabled ? "Đang bật" : "Đã tắt"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-btn" title="Sửa" onClick={() => startEdit(t)}>
                          <Pencil size={15} />
                        </button>
                        <button
                          className="icon-btn"
                          title={t.is_enabled ? "Tắt tác vụ" : "Bật tác vụ"}
                          onClick={() => handleToggleEnabled(t)}
                        >
                          {t.is_enabled ? <PowerOff size={15} /> : <Power size={15} />}
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