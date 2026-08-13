import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Info, Landmark } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { getTaiSanDetail } from "../api/taiSan.js";

const TRANG_THAI_LABELS = {
  DANG_SU_DUNG: "Đang sử dụng",
  CHO_THANH_LY: "Chờ thanh lý",
  DA_THANH_LY: "Đã thanh lý",
  TAM_DUNG_SU_DUNG: "Tạm dừng sử dụng",
};

function formatCurrency(value) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("vi-VN").format(value) + " đ";
}

export default function TaiSanDetailPage() {
  const { id } = useParams();

  const [taiSan, setTaiSan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ---------- Bước 4: Xem chi tiết tài sản -> Hệ thống hiển thị ----------
  useEffect(() => {
    setLoading(true);
    setError(null);
    getTaiSanDetail(id)
      .then((data) => setTaiSan(data))
      .catch((e) => setError(e?.response?.data?.detail?.message || e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <AppLayout
      title={taiSan ? taiSan.ten_tai_san : "Chi tiết tài sản"}
      subtitle="UC-054 — Xem chi tiết tài sản: hệ thống hiển thị đầy đủ thông tin từ curated.dm_tai_san."
    >
      <Link
        to="/tai-san"
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
      ) : taiSan ? (
        <div className="card" style={{ margin: 0, maxWidth: 720 }}>
          <div className="card-header">
            <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Landmark size={16} /> Thông tin tài sản
            </h3>
          </div>
          <div className="card-body">
            <table className="data-table">
              <tbody>
                <tr>
                  <td style={{ color: "#666", width: 180 }}>Mã tài sản</td>
                  <td>{taiSan.ma_tai_san}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Tên tài sản</td>
                  <td>{taiSan.ten_tai_san}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Đơn vị</td>
                  <td>
                    {taiSan.don_vi_ten} ({taiSan.don_vi_code})
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Nhóm tài sản</td>
                  <td>
                    {taiSan.nhom_tai_san_ten} ({taiSan.nhom_tai_san_code})
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Trạng thái</td>
                  <td>
                    <span className="badge">
                      {TRANG_THAI_LABELS[taiSan.trang_thai] || taiSan.trang_thai}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Nguyên giá</td>
                  <td>{formatCurrency(taiSan.nguyen_gia)}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Giá trị còn lại</td>
                  <td>{formatCurrency(taiSan.gia_tri_con_lai)}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Ngày đưa vào sử dụng</td>
                  <td>{taiSan.ngay_dua_vao_su_dung || "-"}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Năm tài chính</td>
                  <td>{taiSan.nam_tai_chinh || "-"}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Ghi chú</td>
                  <td>{taiSan.ghi_chu || "-"}</td>
                </tr>
                <tr>
                  <td style={{ color: "#666" }}>Ngày công bố dữ liệu</td>
                  <td>{taiSan.published_at ? new Date(taiSan.published_at).toLocaleString("vi-VN") : "-"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-body">
            <div className="empty-state">
              <Info size={14} /> Không tìm thấy tài sản.
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}