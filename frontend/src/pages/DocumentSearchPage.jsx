import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileSearch, RefreshCw, Search } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { searchDocuments } from "../api/documents.js";

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

const PAGE_SIZE = 10;

export default function DocumentSearchPage() {
  const { user } = useAuth();
  const userId = user?.id;

  const [keyword, setKeyword] = useState("");
  const [coQuan, setCoQuan] = useState("");
  const [loaiVanBan, setLoaiVanBan] = useState("");
  const [ngayFrom, setNgayFrom] = useState("");
  const [ngayTo, setNgayTo] = useState("");
  const [page, setPage] = useState(1);

  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  // ---------- Bước 1-2: Nhập từ khoá + bộ lọc -> Hệ thống truy vấn
  // OpenSearch + lọc theo quyền -> Hiển thị kết quả thuộc phạm vi quyền ----------
  async function runSearch(nextPage = 1) {
    if (!userId) {
      setError("Không xác định được người dùng hiện tại — vui lòng đăng nhập lại.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await searchDocuments({
        userId,
        keyword,
        coQuan,
        loaiVanBan,
        ngayFrom,
        ngayTo,
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
    if (userId) runSearch(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  function handleSubmit(e) {
    e.preventDefault();
    runSearch(1);
  }

  const totalPages = Math.max(1, Math.ceil(result.total / result.page_size));

  return (
    <AppLayout
      title="Tra cứu dữ liệu văn bản"
      subtitle="UC-053 — Nhập từ khoá + bộ lọc (cơ quan, ngày, loại văn bản), hệ thống truy vấn OpenSearch + lọc theo quyền, hiển thị kết quả thuộc phạm vi quyền."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Bước 1 — Nhập từ khoá + bộ lọc */}
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
                <label>Từ khoá</label>
                <input
                  type="text"
                  placeholder="Số ký hiệu, trích yếu, đơn vị ban hành..."
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Cơ quan / đơn vị ban hành</label>
                <input
                  type="text"
                  placeholder="Vd: Sở Tài chính"
                  value={coQuan}
                  onChange={(e) => setCoQuan(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Loại văn bản</label>
                <select value={loaiVanBan} onChange={(e) => setLoaiVanBan(e.target.value)}>
                  <option value="">Tất cả loại văn bản</option>
                  {Object.entries(LOAI_VAN_BAN_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Ngày ban hành từ</label>
                <input type="date" value={ngayFrom} onChange={(e) => setNgayFrom(e.target.value)} />
              </div>
              <div className="field">
                <label>đến ngày</label>
                <input type="date" value={ngayTo} onChange={(e) => setNgayTo(e.target.value)} />
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

      {/* Bước 2 — Hiển thị kết quả thuộc phạm vi quyền */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <FileSearch size={16} /> Kết quả tra cứu
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
            <div className="empty-state">
              Không tìm thấy văn bản nào phù hợp trong phạm vi quyền của bạn.
            </div>
          ) : result.items.length > 0 ? (
            <>
              <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                Tìm thấy {result.total} văn bản — trang {result.page}/{totalPages}
              </p>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Số ký hiệu</th>
                      <th>Loại văn bản</th>
                      <th>Trích yếu</th>
                      <th>Ngày ban hành</th>
                      <th>Đơn vị ban hành</th>
                      <th>Mức nhạy cảm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((doc) => (
                      <tr key={doc.id}>
                        <td>
                          <Link to={`/documents/${doc.id}`}>{doc.so_ky_hieu}</Link>
                        </td>
                        <td>{LOAI_VAN_BAN_LABELS[doc.loai_van_ban] || doc.loai_van_ban}</td>
                        <td>{doc.trich_yeu}</td>
                        <td>{doc.ngay_ban_hanh}</td>
                        <td>{doc.don_vi_ban_hanh}</td>
                        <td>
                          <span className="badge">
                            {SENSITIVITY_LABELS[doc.sensitivity_level] || doc.sensitivity_level}
                          </span>
                        </td>
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
            <div className="empty-state">Nhập từ khoá hoặc bộ lọc rồi bấm "Tra cứu".</div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}