import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, FileText, Info } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getDocumentDetail, getDocumentFileUrl } from "../api/documents.js";

const LOAI_VAN_BAN_LABELS = {
  QUYET_DINH: "Quyết định",
  CONG_VAN: "Công văn",
  THONG_BAO: "Thông báo",
  NGHI_QUYET: "Nghị quyết",
  CHI_THI: "Chỉ thị",
  KHAC: "Khác",
};

const SENSITIVITY_LABELS = {
  PUBLIC: "Công khai",
  INTERNAL: "Nội bộ",
  CONFIDENTIAL: "Mật",
  SECRET: "Tối mật",
};

export default function DocumentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const userId = user?.id;

  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ---------- Bước 3: Xem chi tiết văn bản -> Hệ thống hiển thị
  // metadata + file PDF ----------
  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    getDocumentDetail(id, userId)
      .then((data) => setDoc(data))
      .catch((e) => setError(e?.response?.data?.detail?.message || e.message))
      .finally(() => setLoading(false));
  }, [id, userId]);

  return (
    <AppLayout
      title={doc ? doc.so_ky_hieu : "Chi tiết văn bản"}
      subtitle="UC-053 — Xem chi tiết văn bản: hệ thống hiển thị metadata + file PDF."
    >
      <Link
        to="/documents"
        className="btn btn-secondary"
        style={{ marginBottom: 12, display: "inline-flex" }}
      >
        <ArrowLeft size={14} /> Quay lại tra cứu
      </Link>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#666" }}>Đang tải...</p>
      ) : doc ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20, alignItems: "start" }}>
          {/* Metadata */}
          <div className="card" style={{ margin: 0 }}>
            <div className="card-header">
              <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Info size={16} /> Siêu dữ liệu
              </h3>
            </div>
            <div className="card-body">
              <table className="data-table">
                <tbody>
                  <tr>
                    <td style={{ color: "#666", width: 150 }}>Số ký hiệu</td>
                    <td>{doc.so_ky_hieu}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "#666" }}>Loại văn bản</td>
                    <td>{LOAI_VAN_BAN_LABELS[doc.loai_van_ban] || doc.loai_van_ban}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "#666" }}>Trích yếu</td>
                    <td>{doc.trich_yeu || "-"}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "#666" }}>Ngày ban hành</td>
                    <td>{doc.ngay_ban_hanh}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "#666" }}>Đơn vị ban hành</td>
                    <td>{doc.don_vi_ban_hanh}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "#666" }}>Mức nhạy cảm</td>
                    <td>
                      <span className="badge">
                        {SENSITIVITY_LABELS[doc.sensitivity_level] || doc.sensitivity_level}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* File PDF */}
          <div className="card" style={{ margin: 0 }}>
            <div className="card-header">
              <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FileText size={16} /> Tệp văn bản (PDF)
              </h3>
            </div>
            <div className="card-body">
              <iframe
                title="document-pdf"
                src={getDocumentFileUrl(doc.id, userId)}
                style={{
                  width: "100%",
                  height: 600,
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                }}
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-body">
            <div className="empty-state">Không tìm thấy văn bản.</div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}