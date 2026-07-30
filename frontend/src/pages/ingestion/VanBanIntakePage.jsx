import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Upload } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import { listDataSources } from "../../api/dataSources.js";
import { listVanBanDocuments, submitVanBanDocument } from "../../api/vanBanIntake.js";

const STATUS_BADGE = {
  RECEIVED: "badge-success",
  DUPLICATE_SKIPPED: "badge-warning",
};

const STATUS_LABEL = {
  RECEIVED: "Đã tiếp nhận",
  DUPLICATE_SKIPPED: "Bản trùng (đã bỏ qua)",
};

const EMPTY_FORM = {
  dataSourceId: "",
  soKyHieu: "",
  loaiVanBan: "",
  trichYeu: "",
  ngayBanHanh: "",
  donViBanHanh: "",
  uploadedBy: "canbo01",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function VanBanIntakePage() {
  const [dataSources, setDataSources] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [file, setFile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function loadDataSources() {
    try {
      const sources = await listDataSources({ sourceSystem: "QLVBDH" });
      setDataSources(sources);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function reloadDocuments() {
    setLoading(true);
    try {
      const data = await listVanBanDocuments({
        dataSourceId: form.dataSourceId ? Number(form.dataSourceId) : null,
        status: statusFilter || null,
      });
      setDocuments(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDataSources();
  }, []);

  useEffect(() => {
    reloadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.dataSourceId, statusFilter]);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 4000);
  }

  function dataSourceLabel(id) {
    const ds = dataSources.find((d) => d.id === id);
    return ds ? `${ds.code} — ${ds.name}` : `#${id}`;
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.dataSourceId) {
      setError("Vui lòng chọn nguồn dữ liệu QLVBĐH");
      return;
    }
    if (!file) {
      setError("Vui lòng chọn tệp PDF/bản quét đính kèm");
      return;
    }
    setSubmitting(true);
    try {
      const doc = await submitVanBanDocument({
        dataSourceId: Number(form.dataSourceId),
        soKyHieu: form.soKyHieu,
        loaiVanBan: form.loaiVanBan,
        trichYeu: form.trichYeu,
        ngayBanHanh: form.ngayBanHanh,
        donViBanHanh: form.donViBanHanh,
        uploadedBy: form.uploadedBy,
        file,
      });
      setFile(null);
      if (document.getElementById("van-ban-file-input")) {
        document.getElementById("van-ban-file-input").value = "";
      }
      if (doc.status === "DUPLICATE_SKIPPED") {
        setError(
          `Văn bản có số ký hiệu '${doc.so_ky_hieu}' đã được tiếp nhận trước đó — hệ thống bỏ qua bản trùng.`
        );
      } else {
        flashSuccess(
          `Tiếp nhận thành công văn bản '${doc.so_ky_hieu}' — đã lưu vào staging.stg_van_ban, ` +
            `tệp đính kèm đã lưu vào MinIO và đã kích hoạt sự kiện ocr.requested.`
        );
        setError(null);
        setForm((prev) => ({ ...EMPTY_FORM, dataSourceId: prev.dataSourceId, uploadedBy: prev.uploadedBy }));
      }
      await reloadDocuments();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Tiếp nhận thủ công văn bản từ QLVBĐH (upload định kỳ)"
      subtitle="UC-024 — Nhập siêu dữ liệu văn bản + đính kèm tệp PDF/bản quét: hệ thống lưu vào staging.stg_van_ban + MinIO (raw-documents), khử trùng lặp theo số ký hiệu, kích hoạt sự kiện ocr.requested."
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
          <h2>Nộp văn bản</h2>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="van-ban-data-source">Nguồn dữ liệu QLVBĐH</label>
                <select
                  id="van-ban-data-source"
                  value={form.dataSourceId}
                  onChange={(e) => updateField("dataSourceId", e.target.value)}
                  required
                >
                  <option value="" disabled>
                    -- Chọn nguồn dữ liệu (QLVBĐH) --
                  </option>
                  {dataSources.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.code} — {s.name}
                    </option>
                  ))}
                </select>
                {dataSources.length === 0 && (
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Chưa có nguồn dữ liệu QLVBĐH nào được đăng ký (xem trang "Nguồn dữ liệu").
                  </div>
                )}
              </div>
              <div className="field">
                <label htmlFor="van-ban-so-ky-hieu">Số ký hiệu</label>
                <input
                  id="van-ban-so-ky-hieu"
                  value={form.soKyHieu}
                  onChange={(e) => updateField("soKyHieu", e.target.value)}
                  placeholder="vd 123/QĐ-BTC"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="van-ban-loai">Loại văn bản</label>
                <input
                  id="van-ban-loai"
                  value={form.loaiVanBan}
                  onChange={(e) => updateField("loaiVanBan", e.target.value)}
                  placeholder="vd Quyết định, Công văn, Thông tư..."
                  required
                />
              </div>
              <div className="field" style={{ gridColumn: "1 / -1" }}>
                <label htmlFor="van-ban-trich-yeu">Trích yếu</label>
                <input
                  id="van-ban-trich-yeu"
                  value={form.trichYeu}
                  onChange={(e) => updateField("trichYeu", e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="van-ban-ngay-ban-hanh">Ngày ban hành</label>
                <input
                  id="van-ban-ngay-ban-hanh"
                  type="date"
                  value={form.ngayBanHanh}
                  onChange={(e) => updateField("ngayBanHanh", e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="van-ban-don-vi-ban-hanh">Đơn vị ban hành</label>
                <input
                  id="van-ban-don-vi-ban-hanh"
                  value={form.donViBanHanh}
                  onChange={(e) => updateField("donViBanHanh", e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="van-ban-uploaded-by">Cán bộ nộp văn bản</label>
                <input
                  id="van-ban-uploaded-by"
                  value={form.uploadedBy}
                  onChange={(e) => updateField("uploadedBy", e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="van-ban-file-input">Tệp PDF/bản quét đính kèm</label>
                <input
                  id="van-ban-file-input"
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  required
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  <Upload size={15} />
                  {submitting ? "Đang nộp..." : "Nộp văn bản"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Lịch sử văn bản đã tiếp nhận ({documents.length})</h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="RECEIVED">Đã tiếp nhận</option>
            <option value="DUPLICATE_SKIPPED">Bản trùng (đã bỏ qua)</option>
          </select>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : documents.length === 0 ? (
            <div className="empty-state">Chưa có văn bản nào được tiếp nhận.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Số ký hiệu</th>
                  <th>Loại văn bản</th>
                  <th>Trích yếu</th>
                  <th>Ngày ban hành</th>
                  <th>Đơn vị ban hành</th>
                  <th>Nguồn dữ liệu</th>
                  <th>Trạng thái</th>
                  <th>Cán bộ nộp</th>
                  <th>Thời gian</th>
                  <th>Sự kiện OCR</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td>{d.id}</td>
                    <td>{d.so_ky_hieu}</td>
                    <td>{d.loai_van_ban}</td>
                    <td>{d.trich_yeu}</td>
                    <td>{d.ngay_ban_hanh}</td>
                    <td>{d.don_vi_ban_hanh}</td>
                    <td>{dataSourceLabel(d.data_source_id)}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[d.status] || "badge-neutral"}`}>
                        {STATUS_LABEL[d.status] || d.status}
                      </span>
                    </td>
                    <td>{d.uploaded_by}</td>
                    <td>{formatTime(d.uploaded_at)}</td>
                    <td>{d.ocr_event_published ? "Đã đẩy sự kiện" : "—"}</td>
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