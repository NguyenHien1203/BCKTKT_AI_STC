import { useEffect, useState } from "react";
import { RefreshCw, Search, Wallet } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { getNganSachDetail, searchNganSach } from "../api/nganSach.js";

const PAGE_SIZE = 10;

function formatSo(value) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("vi-VN").format(value);
}

export default function NganSachPage() {
  const [donVi, setDonVi] = useState("");
  const [khoanMuc, setKhoanMuc] = useState("");
  const [kyFrom, setKyFrom] = useState("");
  const [kyTo, setKyTo] = useState("");
  const [page, setPage] = useState(1);

  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  // Bước 4-5 — Xem chi tiết theo đơn vị/khoản mục -> Hệ thống re-query.
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // ---------- Bước 1-3: Nhập bộ lọc (đơn vị, khoản mục, kỳ) -> Hệ
  // thống truy vấn curated.dm_ngan_sach -> Hiển thị số liệu thu/chi/tạm
  // ứng ----------
  async function runSearch(nextPage = 1) {
    setLoading(true);
    setError(null);
    try {
      const data = await searchNganSach({
        donVi, khoanMuc, kyFrom, kyTo, page: nextPage, pageSize: PAGE_SIZE,
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

  // ---------- Bước 4-5: Xem chi tiết theo đơn vị/khoản mục -> Hệ
  // thống re-query ----------
  async function viewDetail(donViCode, khoanMucCode) {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const data = await getNganSachDetail({ donViCode, khoanMucCode });
      setDetail(data);
    } catch (e) {
      setDetailError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(result.total / result.page_size));

  return (
    <AppLayout
      title="Tra cứu dữ liệu ngân sách"
      subtitle="UC-056 — Nhập bộ lọc (đơn vị, khoản mục, kỳ), hệ thống truy vấn curated.dm_ngan_sach, hiển thị số liệu thu/chi/tạm ứng; xem chi tiết theo đơn vị/khoản mục để hệ thống re-query."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Bước 1 — Nhập bộ lọc (đơn vị, khoản mục, kỳ) */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Search size={16} /> Bộ lọc tra cứu ngân sách
          </h3>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label>Đơn vị</label>
                <input
                  type="text"
                  placeholder="Vd: Sở Tài chính, SO_TC..."
                  value={donVi}
                  onChange={(e) => setDonVi(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Khoản mục</label>
                <input
                  type="text"
                  placeholder="Vd: Sự nghiệp kinh tế, KM_SNKT..."
                  value={khoanMuc}
                  onChange={(e) => setKhoanMuc(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Kỳ từ (năm)</label>
                <input
                  type="number"
                  placeholder="Vd: 2024"
                  value={kyFrom}
                  onChange={(e) => setKyFrom(e.target.value)}
                />
              </div>
              <div className="field">
                <label>đến kỳ (năm)</label>
                <input
                  type="number"
                  placeholder="Vd: 2026"
                  value={kyTo}
                  onChange={(e) => setKyTo(e.target.value)}
                />
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

      {/* Bước 4-5 — Xem chi tiết theo đơn vị/khoản mục -> Hệ thống re-query */}
      {(detail || detailLoading || detailError) && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Wallet size={16} /> Chi tiết theo đơn vị/khoản mục
            </h3>
          </div>
          <div className="card-body">
            {detailLoading ? (
              <p style={{ color: "#666" }}>Đang re-query chi tiết...</p>
            ) : detailError ? (
              <div className="alert alert-error">{detailError}</div>
            ) : detail ? (
              <>
                <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                  Đơn vị <strong>{detail.don_vi_code}</strong> — Khoản mục{" "}
                  <strong>{detail.khoan_muc_code}</strong>
                </p>
                <div style={{ display: "flex", gap: 24, marginBottom: 14, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#666" }}>Tổng thu</div>
                    <div style={{ fontSize: 18, fontWeight: 600 }}>{formatSo(detail.tong_thu)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#666" }}>Tổng chi</div>
                    <div style={{ fontSize: 18, fontWeight: 600 }}>{formatSo(detail.tong_chi)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#666" }}>Tổng tạm ứng</div>
                    <div style={{ fontSize: 18, fontWeight: 600 }}>
                      {formatSo(detail.tong_tam_ung)}
                    </div>
                  </div>
                </div>
                {detail.items.length === 0 ? (
                  <div className="empty-state">Không có số liệu theo kỳ cho đơn vị/khoản mục này.</div>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Kỳ</th>
                          <th>Thu</th>
                          <th>Chi</th>
                          <th>Tạm ứng</th>
                          <th>Đơn vị tính</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.items.map((row) => (
                          <tr key={row.id}>
                            <td>{row.ky}</td>
                            <td>{formatSo(row.thu)}</td>
                            <td>{formatSo(row.chi)}</td>
                            <td>{formatSo(row.tam_ung)}</td>
                            <td>{row.don_vi_tinh}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* Bước 2-3 — Hiển thị số liệu thu/chi/tạm ứng */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Wallet size={16} /> Số liệu ngân sách (thu/chi/tạm ứng)
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
            <div className="empty-state">Không tìm thấy số liệu ngân sách nào phù hợp bộ lọc.</div>
          ) : result.items.length > 0 ? (
            <>
              <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                Tìm thấy {result.total} bản ghi — trang {result.page}/{totalPages}
              </p>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Đơn vị</th>
                      <th>Khoản mục</th>
                      <th>Kỳ</th>
                      <th>Thu</th>
                      <th>Chi</th>
                      <th>Tạm ứng</th>
                      <th>Đơn vị tính</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {row.don_vi_ten}{" "}
                          <span style={{ color: "#999", fontSize: 11 }}>({row.don_vi_code})</span>
                        </td>
                        <td>
                          {row.khoan_muc_ten}{" "}
                          <span style={{ color: "#999", fontSize: 11 }}>
                            ({row.khoan_muc_code})
                          </span>
                        </td>
                        <td>{row.ky}</td>
                        <td>{formatSo(row.thu)}</td>
                        <td>{formatSo(row.chi)}</td>
                        <td>{formatSo(row.tam_ung)}</td>
                        <td>{row.don_vi_tinh}</td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => viewDetail(row.don_vi_code, row.khoan_muc_code)}
                          >
                            Xem chi tiết
                          </button>
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
            <div className="empty-state">Nhập bộ lọc rồi bấm "Tra cứu".</div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}