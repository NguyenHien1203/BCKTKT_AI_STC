import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Download, Eye, Upload } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import { listDatasets } from "../../api/datasets.js";
import {
  downloadUploadTemplate,
  listTabmisIntakeSessions,
  uploadTabmisFile,
} from "../../api/tabmisIntake.js";

const STATUS_BADGE = {
  RECEIVED: "badge-success",
  TEMPLATE_INVALID: "badge-danger",
  ROW_ERRORS: "badge-warning",
  CORRECTED: "badge-success",
};

const STATUS_LABEL = {
  RECEIVED: "Đã tiếp nhận",
  TEMPLATE_INVALID: "Sai biểu mẫu",
  ROW_ERRORS: "Có dòng dữ liệu sai",
  CORRECTED: "Đã sửa & kiểm tra lại thành công",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function TabmisIntakePage() {
  const [dataSources, setDataSources] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState("");
  const [uploadedBy, setUploadedBy] = useState("canbo01");
  const [file, setFile] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");

  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function loadTabmisDatasets() {
    try {
      const sources = await listDataSources({ sourceSystem: "TABMIS" });
      setDataSources(sources);
      const perSource = await Promise.all(
        sources.map((s) => listDatasets({ dataSourceId: s.id }))
      );
      setDatasets(perSource.flat());
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function reloadSessions() {
    if (!datasetId) {
      setSessions([]);
      return;
    }
    setLoading(true);
    try {
      const data = await listTabmisIntakeSessions({
        datasetId: Number(datasetId),
        status: statusFilter || null,
      });
      setSessions(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTabmisDatasets();
  }, []);

  useEffect(() => {
    reloadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, statusFilter]);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 4000);
  }

  function datasetLabel(id) {
    const ds = datasets.find((d) => d.id === id);
    return ds ? `${ds.code} — ${ds.name}` : `#${id}`;
  }

  async function handleDownloadTemplate() {
    if (!datasetId) {
      setError("Vui lòng chọn tập dữ liệu TABMIS trước khi tải biểu mẫu");
      return;
    }
    try {
      const { blob } = await downloadUploadTemplate(Number(datasetId));
      const ds = datasets.find((d) => d.id === Number(datasetId));
      const fileName = `tabmis-${ds ? ds.code : datasetId}-bieu-mau.xlsx`;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!datasetId) {
      setError("Vui lòng chọn tập dữ liệu TABMIS");
      return;
    }
    if (!file) {
      setError("Vui lòng chọn tệp Excel đã điền để tải lên");
      return;
    }
    setUploading(true);
    try {
      const session = await uploadTabmisFile({
        datasetId: Number(datasetId),
        uploadedBy,
        file,
      });
      setFile(null);
      if (document.getElementById("tabmis-file-input")) {
        document.getElementById("tabmis-file-input").value = "";
      }
      if (session.status === "RECEIVED") {
        flashSuccess(
          `Tiếp nhận thành công: đã đọc ${session.control_totals.records_read} dòng dữ liệu, ` +
            `tạo phiên ingest #${session.ingestion_run_id}.`
        );
        setError(null);
      } else {
        setError(`Tệp sai biểu mẫu: ${session.error_message}`);
      }
      await reloadSessions();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <AppLayout
      title="Tiếp nhận file thủ công TABMIS (upload)"
      subtitle="UC-022 — Tải biểu mẫu Excel chuẩn, tải tệp đã điền lên: hệ thống lưu raw vào MinIO, kiểm tra đúng biểu mẫu + tổng kiểm soát, tạo phiên tiếp nhận mới và ghi vào ingestion.runs."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{success}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Bước 1-2 — Tải biểu mẫu &amp; tải tệp lên</h2>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="field">
              <label htmlFor="dataset_id">Tập dữ liệu TABMIS</label>
              <select
                id="dataset_id"
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
                required
              >
                <option value="" disabled>
                  -- Chọn tập dữ liệu (nguồn TABMIS) --
                </option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
              {dataSources.length === 0 && (
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                  Chưa có nguồn dữ liệu TABMIS nào được đăng ký (xem trang "Nguồn dữ liệu").
                </div>
              )}
            </div>
          </div>

          <div style={{ marginTop: 8, marginBottom: 20 }}>
            <button
              type="button"
              className="btn"
              onClick={handleDownloadTemplate}
              disabled={!datasetId}
            >
              <Download size={15} />
              Tải biểu mẫu Excel chuẩn
            </button>
          </div>

          <form onSubmit={handleUpload}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="uploaded_by">Cán bộ nộp file</label>
                <input
                  id="uploaded_by"
                  value={uploadedBy}
                  onChange={(e) => setUploadedBy(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="tabmis-file-input">Tệp Excel đã điền (.xlsx)</label>
                <input
                  id="tabmis-file-input"
                  type="file"
                  accept=".xlsx,.xlsm"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  required
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  <Upload size={15} />
                  {uploading ? "Đang tải lên..." : "Tải tệp lên"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Lịch sử phiên tiếp nhận ({sessions.length})</h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="RECEIVED">Đã tiếp nhận</option>
            <option value="TEMPLATE_INVALID">Sai biểu mẫu</option>
            <option value="ROW_ERRORS">Có dòng dữ liệu sai</option>
            <option value="CORRECTED">Đã sửa & kiểm tra lại thành công</option>
          </select>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {!datasetId ? (
            <div className="empty-state">Chọn 1 tập dữ liệu TABMIS ở trên để xem lịch sử.</div>
          ) : loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : sessions.length === 0 ? (
            <div className="empty-state">Chưa có phiên tiếp nhận nào cho tập dữ liệu này.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tệp</th>
                  <th>Tập dữ liệu</th>
                  <th>Trạng thái</th>
                  <th>Tổng kiểm soát</th>
                  <th>Cán bộ nộp</th>
                  <th>Thời gian</th>
                  <th>Phiên ingest</th>
                  <th>UC-023</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{s.file_name}</td>
                    <td>{datasetLabel(s.dataset_id)}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[s.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[s.status] || s.status}
                      </span>
                      {s.error_message && (
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {s.error_message}
                        </div>
                      )}
                    </td>
                    <td>
                      {s.control_totals?.records_read ?? 0} dòng /{" "}
                      {s.control_totals?.columns_found ?? 0}/{s.control_totals?.columns_expected ?? 0}{" "}
                      cột
                      {typeof s.control_totals?.row_error_count === "number" &&
                        s.control_totals.row_error_count > 0 && (
                          <div style={{ fontSize: 12, color: "var(--color-warning)" }}>
                            {s.control_totals.row_error_count} dòng sai
                          </div>
                        )}
                    </td>
                    <td>{s.uploaded_by}</td>
                    <td>{formatTime(s.uploaded_at)}</td>
                    <td>{s.ingestion_run_id ? `#${s.ingestion_run_id}` : "—"}</td>
                    <td>
                      <Link
                        to={`/tabmis-intake/${s.id}`}
                        className="btn"
                        style={{ padding: "4px 10px", fontSize: 12 }}
                      >
                        <Eye size={14} />
                        Xem trạng thái / sửa lỗi
                      </Link>
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