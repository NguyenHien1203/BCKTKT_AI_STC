import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, CheckCircle2, ListChecks, Upload } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  getTabmisIntakeRowErrors,
  getTabmisIntakeStatus,
  reuploadTabmisIntakeFile,
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

// UC-023 bước 1: máy trạng thái — mô tả các trạng thái + hướng đi tiếp theo,
// dùng để vẽ sơ đồ trực quan cho người dùng.
const STATE_MACHINE_ORDER = ["TEMPLATE_INVALID", "ROW_ERRORS", "RECEIVED", "CORRECTED"];

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function TabmisIntakeDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);

  const [statusView, setStatusView] = useState(null);
  const [rowErrors, setRowErrors] = useState([]);
  const [uploadedBy, setUploadedBy] = useState("canbo01");
  const [file, setFile] = useState(null);

  const [loading, setLoading] = useState(true);
  const [reuploading, setReuploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function reload() {
    setLoading(true);
    try {
      const view = await getTabmisIntakeStatus(sessionId);
      setStatusView(view);
      if (view.allowed_actions.includes("VIEW_ROW_ERRORS")) {
        const errors = await getTabmisIntakeRowErrors(sessionId);
        setRowErrors(errors);
      } else {
        setRowErrors([]);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 5000);
  }

  async function handleReupload(e) {
    e.preventDefault();
    if (!file) {
      setError("Vui lòng chọn tệp Excel đã sửa để tải lại");
      return;
    }
    setReuploading(true);
    try {
      const updated = await reuploadTabmisIntakeFile({ sessionId, uploadedBy, file });
      setFile(null);
      const fileInput = document.getElementById("tabmis-reupload-input");
      if (fileInput) fileInput.value = "";
      if (updated.status === "CORRECTED" || updated.status === "RECEIVED") {
        flashSuccess(
          `Hệ thống đã kiểm tra lại: tệp hợp lệ, không còn lỗi (phiên ingest mới #${updated.ingestion_run_id}).`
        );
        setError(null);
      } else {
        setError(
          `Hệ thống đã kiểm tra lại nhưng tệp vẫn còn lỗi: ${updated.error_message}`
        );
      }
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setReuploading(false);
    }
  }

  const session = statusView?.session;

  return (
    <AppLayout
      title={`Phiên tiếp nhận TABMIS #${sessionId}`}
      subtitle="UC-023 — Xem trạng thái tiếp nhận (máy trạng thái), xem chi tiết lỗi dòng, sửa và tải lại tệp đã chỉnh để hệ thống kiểm tra lại."
    >
      <div style={{ marginBottom: 16 }}>
        <Link to="/tabmis-intake" className="btn">
          <ArrowLeft size={15} />
          Quay lại danh sách phiên tiếp nhận
        </Link>
      </div>

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

      {loading && !session ? (
        <div className="empty-state">Đang tải dữ liệu...</div>
      ) : !session ? null : (
        <>
          {/* Bước 1: Xem trạng thái tiếp nhận -> hệ thống hiển thị máy trạng thái */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h2>Bước 1 — Trạng thái tiếp nhận</h2>
            </div>
            <div className="card-body">
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <span className={`badge ${STATUS_BADGE[session.status] || "badge-neutral"}`}>
                  {STATUS_LABEL[session.status] || session.status}
                </span>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                  Tệp: {session.file_name} — Nộp bởi {session.uploaded_by} lúc{" "}
                  {formatTime(session.uploaded_at)}
                </span>
              </div>

              {/* Sơ đồ máy trạng thái đơn giản */}
              <div
                style={{
                  marginTop: 16,
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                {STATE_MACHINE_ORDER.map((st, idx) => (
                  <span key={st} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      className={`badge ${
                        st === session.status ? STATUS_BADGE[st] : "badge-neutral"
                      }`}
                      style={{
                        opacity: st === session.status ? 1 : 0.55,
                        fontWeight: st === session.status ? 700 : 500,
                      }}
                    >
                      {STATUS_LABEL[st]}
                    </span>
                    {idx < STATE_MACHINE_ORDER.length - 1 && (
                      <span style={{ color: "var(--color-text-secondary)" }}>→</span>
                    )}
                  </span>
                ))}
              </div>

              <div style={{ marginTop: 16 }}>
                <table className="data-table">
                  <tbody>
                    <tr>
                      <td style={{ width: 220 }}>Số dòng dữ liệu đọc được</td>
                      <td>{session.control_totals?.records_read ?? 0}</td>
                    </tr>
                    <tr>
                      <td>Số cột khớp / kỳ vọng</td>
                      <td>
                        {session.control_totals?.columns_found ?? 0} /{" "}
                        {session.control_totals?.columns_expected ?? 0}
                      </td>
                    </tr>
                    <tr>
                      <td>Số dòng dữ liệu sai</td>
                      <td>{statusView.row_error_count}</td>
                    </tr>
                    <tr>
                      <td>Phiên ingest gắn kèm</td>
                      <td>
                        {session.ingestion_run_id ? `#${session.ingestion_run_id}` : "—"}
                      </td>
                    </tr>
                  </tbody>
                </table>
                {session.error_message && (
                  <div className="alert alert-error" style={{ marginTop: 12 }}>
                    <AlertCircle size={16} />
                    <span>{session.error_message}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bước 2: Xem chi tiết lỗi dòng -> hệ thống hiển thị các dòng sai */}
          {statusView.allowed_actions.includes("VIEW_ROW_ERRORS") && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-header">
                <h2>
                  <ListChecks size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
                  Bước 2 — Chi tiết lỗi dòng ({rowErrors.length})
                </h2>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                {rowErrors.length === 0 ? (
                  <div className="empty-state">
                    Tệp sai biểu mẫu (thiếu cột bắt buộc) nên hệ thống chưa kiểm tra được
                    lỗi từng dòng — vui lòng sửa đủ cột trước.
                  </div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Dòng số</th>
                        <th>Trường</th>
                        <th>Nội dung lỗi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rowErrors.map((err) => (
                        <tr key={err.id}>
                          <td>{err.row_number}</td>
                          <td>{err.field_name}</td>
                          <td>{err.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {/* Bước 3: Sửa và tải lại tệp đã chỉnh -> hệ thống kiểm tra lại */}
          <div className="card">
            <div className="card-header">
              <h2>Bước 3 — Sửa và tải lại tệp đã chỉnh</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleReupload}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="reupload-uploaded-by">Cán bộ nộp file</label>
                    <input
                      id="reupload-uploaded-by"
                      value={uploadedBy}
                      onChange={(e) => setUploadedBy(e.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="tabmis-reupload-input">Tệp Excel đã sửa (.xlsx)</label>
                    <input
                      id="tabmis-reupload-input"
                      type="file"
                      accept=".xlsx,.xlsm"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                      required
                    />
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end" }}>
                    <button type="submit" className="btn btn-primary" disabled={reuploading}>
                      <Upload size={15} />
                      {reuploading ? "Đang kiểm tra lại..." : "Tải lại & kiểm tra lại"}
                    </button>
                  </div>
                </div>
              </form>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 8 }}>
                Hệ thống sẽ kiểm tra lại đúng biểu mẫu (cột) + lỗi từng dòng (trường bắt
                buộc/kiểu dữ liệu) trên cùng phiên tiếp nhận này, và ghi 1 phiên ingest mới
                vào lịch sử chạy.
              </div>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}