import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Inbox, RefreshCw, XCircle } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDatasets } from "../../api/datasets.js";
import {
  listUnmappedQueueItems,
  resolveUnmappedQueueItem,
} from "../../api/unmappedQueue.js";

const STATUS_BADGE = {
  PENDING: "badge-warning",
  RESOLVED: "badge-success",
};

const STATUS_LABEL = {
  PENDING: "Chưa xử lý",
  RESOLVED: "Đã xử lý",
};

const ACTION_LABEL = {
  MAP: "Ánh xạ",
  CREATE_NEW: "Tạo mục mới",
  REJECT: "Từ chối",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

/** Form xử lý 1 mục hàng đợi (bước 2-3), hiển thị trực tiếp trên dòng bảng. */
function ResolveForm({ item, onResolved, onError }) {
  const [action, setAction] = useState("MAP");
  const [standardValue, setStandardValue] = useState("");
  const [reason, setReason] = useState("");
  const [applyToSimilar, setApplyToSimilar] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const result = await resolveUnmappedQueueItem(item.id, {
        action,
        standardValue: action === "REJECT" ? null : standardValue,
        reason: action === "REJECT" ? reason : null,
        applyToSimilar,
      });
      onResolved(result);
      onError(null);
    } catch (e) {
      onError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
      <select value={action} onChange={(e) => setAction(e.target.value)} style={{ minWidth: 130 }}>
        <option value="MAP">Ánh xạ</option>
        <option value="CREATE_NEW">Tạo mục mới</option>
        <option value="REJECT">Từ chối</option>
      </select>
      {action === "REJECT" ? (
        <input
          type="text"
          placeholder="Lý do từ chối..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ minWidth: 200 }}
        />
      ) : (
        <input
          type="text"
          placeholder="Giá trị chuẩn..."
          value={standardValue}
          onChange={(e) => setStandardValue(e.target.value)}
          style={{ minWidth: 160 }}
        />
      )}
      <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
        <input
          type="checkbox"
          checked={applyToSimilar}
          onChange={(e) => setApplyToSimilar(e.target.checked)}
        />
        Áp dụng cho các giá trị tương tự
      </label>
      <button
        className="btn btn-primary"
        onClick={handleSubmit}
        disabled={
          submitting ||
          (action !== "REJECT" && !standardValue.trim()) ||
          (action === "REJECT" && !reason.trim())
        }
      >
        {submitting ? "Đang lưu..." : "Xử lý"}
      </button>
    </div>
  );
}

export default function UnmappedQueuePage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [fieldNameFilter, setFieldNameFilter] = useState("");
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
      const data = await listUnmappedQueueItems({
        datasetId: selectedDatasetId ? Number(selectedDatasetId) : null,
        fieldName: fieldNameFilter.trim() || null,
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
  }, [selectedDatasetId, fieldNameFilter, statusFilter]);

  function handleResolved(result) {
    const affected = result.affected_count || 0;
    setInfo(
      affected > 0
        ? `Đã xử lý giá trị #${result.item.id} và áp dụng đồng loạt cho ${affected} giá trị tương tự khác.`
        : `Đã xử lý giá trị #${result.item.id}.`,
    );
    loadQueue();
  }

  return (
    <AppLayout
      title="Xử lý hàng đợi chưa ánh xạ"
      subtitle="UC-032 — Xem hàng đợi chưa ánh xạ do UC-031 đẩy vào; xử lý từng giá trị (ánh xạ sang giá trị chuẩn / tạo mục danh mục mới / từ chối), hệ thống lưu mapping mới; có thể áp dụng đồng loạt cho các giá trị tương tự."
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
          <h2>Bước 1 — Xem hàng đợi chưa ánh xạ</h2>
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
              <label htmlFor="field-filter">Trường</label>
              <input
                id="field-filter"
                type="text"
                placeholder="vd: loai_don_vi"
                value={fieldNameFilter}
                onChange={(e) => setFieldNameFilter(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="status-filter">Trạng thái</label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="PENDING">Chưa xử lý</option>
                <option value="RESOLVED">Đã xử lý</option>
                <option value="ALL">Tất cả</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>
            <Inbox size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Hàng đợi ({items.length})
          </h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">Không có mục nào trong hàng đợi phù hợp bộ lọc.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tập dữ liệu</th>
                  <th>Trường</th>
                  <th>Giá trị nguồn</th>
                  <th>Trạng thái</th>
                  <th>Kết quả xử lý</th>
                  <th>Tạo lúc</th>
                  <th style={{ minWidth: 380 }}>Xử lý (bước 2 + 3)</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.id}</td>
                    <td>{it.dataset_id}</td>
                    <td>{it.field_name}</td>
                    <td>{it.raw_value}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[it.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[it.status] || it.status}
                      </span>
                    </td>
                    <td>
                      {it.status === "RESOLVED" ? (
                        it.resolution_action === "REJECT" ? (
                          <span title={it.resolution_reason}>
                            <XCircle
                              size={14}
                              style={{ color: "var(--color-danger)", verticalAlign: "middle" }}
                            />{" "}
                            {ACTION_LABEL[it.resolution_action]}
                          </span>
                        ) : (
                          <span>
                            <CheckCircle2
                              size={14}
                              style={{ color: "var(--color-success)", verticalAlign: "middle" }}
                            />{" "}
                            {ACTION_LABEL[it.resolution_action]}: <strong>{it.resolved_value}</strong>
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