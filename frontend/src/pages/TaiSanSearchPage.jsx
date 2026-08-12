import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Landmark, RefreshCw, Search } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { searchTaiSan } from "../api/taiSan.js";

const TRANG_THAI_LABELS = {
  DANG_SU_DUNG: "Đang sử dụng",
  CHO_THANH_LY: "Chờ thanh lý",
  DA_THANH_LY: "Đã thanh lý",
  TAM_DUNG_SU_DUNG: "Tạm dừng sử dụng",
};

const PAGE_SIZE = 10;

function formatCurrency(value) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("vi-VN").format(value) + " đ";
}

export default function TaiSanSearchPage() {
  const [donViCode, setDonViCode] = useState("");
  const [nhomTaiSanCode, setNhomTaiSanCode] = useState("");
  const [trangThai, setTrangThai] = useState("");
  const [page, setPage] = useState(1);

  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  // ---------- Bước 1-3: Nhập bộ lọc (đơn vị, nhóm, trạng thái) -> Hệ
  // thống truy vấn curated.dm_tai_san -> Hiển thị danh sách tài sản ----------
  async function runSearch(nextPage = 1) {
    setLoading(true);
    setError(null);
    try {
      const data = await searchTaiSan({
        donViCode,
        nhomTaiSanCode,
        trangThai,
        page: nextPage,
        pageSize: PAGE_SIZE,
      });
      setResult(data);
      setPage(nextPage);
      setSearched(true);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runSearch(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    runSearch(1);
  }

  const totalPages = Math.max(1, Math.ceil(result.total / result.page_size));

  return (
    <AppLayout
      title="Tra cứu dữ liệu tài sản"
      subtitle="UC-054 — Nhập bộ lọc (đơn vị, nhóm, trạng thái), hệ thống truy vấn curated.dm_tai_san, hiển thị danh sách tài sản; xem chi tiết tài sản."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Bước 1 — Nhập bộ lọc (đơn vị, nhóm, trạng thái) */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Search size={16} /> Bộ lọc tra cứu
          </h3>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label>Đơn vị</label>
                <input
                  type="text"
                  placeholder="Vd: DV001"
                  value={donViCode}
                  onChange={(e) => setDonViCode(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Nhóm tài sản</label>
                <input
                  type="text"
                  placeholder="Vd: NHOM_NHA_DAT"
                  value={nhomTaiSanCode}
                  onChange={(e) => setNhomTaiSanCode(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Trạng thái</label>
                <select value={trangThai} onChange={(e) => setTrangThai(e.target.value)}>
                  <option value="">Tất cả trạng thái</option>
                  {Object.entries(TRANG_THAI_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ marginTop: 12 }}
            >
              <Search size={14} /> {loading ? "Đang tra cứu..." : "Tra cứu"}
            </button>
          </form>
        </div>
      </div>

      {/* Bước 3 — Hiển thị danh sách tài sản */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Landmark size={16} /> Danh sách tài sản
          </h3>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => runSearch(page)}
            disabled={loading}
          >
            <RefreshCw size={14} /> Tải lại
          </button>
        </div>
        <div className="card-body">
          {loading ? (
            <p style={{ color: "#666" }}>Đang tra cứu...</p>
          ) : searched && result.items.length === 0 ? (
            <div className="empty-state">Không tìm thấy tài sản nào phù hợp với bộ lọc.</div>
          ) : result.items.length > 0 ? (
            <>
              <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                Tìm thấy {result.total} tài sản — trang {result.page}/{totalPages}
              </p>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mã tài sản</th>
                      <th>Tên tài sản</th>
                      <th>Đơn vị</th>
                      <th>Nhóm tài sản</th>
                      <th>Trạng thái</th>
                      <th>Nguyên giá</th>
                      <th>Giá trị còn lại</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((ts) => (
                      <tr key={ts.id}>
                        <td>
                          <Link to={`/tai-san/${ts.id}`}>{ts.ma_tai_san}</Link>
                        </td>
                        <td>{ts.ten_tai_san}</td>
                        <td>{ts.don_vi_ten}</td>
                        <td>{ts.nhom_tai_san_ten}</td>
                        <td>
                          <span className="badge">
                            {TRANG_THAI_LABELS[ts.trang_thai] || ts.trang_thai}
                          </span>
                        </td>
                        <td>{formatCurrency(ts.nguyen_gia)}</td>
                        <td>{formatCurrency(ts.gia_tri_con_lai)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 14 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={page <= 1 || loading}
                  onClick={() => runSearch(page - 1)}
                >
                  Trang trước
                </button>
                <span style={{ fontSize: 12, color: "#666" }}>
                  Trang {page}/{totalPages}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={page >= totalPages || loading}
                  onClick={() => runSearch(page + 1)}
                >
                  Trang sau
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">Nhập bộ lọc rồi bấm "Tra cứu".</div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}