import { useEffect, useState } from "react";
import { LineChart, RefreshCw, Search } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { getPriceTrend, searchPriceData } from "../api/priceData.js";

const PAGE_SIZE = 10;

// ---------- Bước 3-4: Hiển thị biểu đồ xu hướng giá theo thời gian ->
// Hệ thống hiển thị line chart. Tự vẽ bằng SVG, không cần thêm thư viện. ----------
function PriceTrendChart({ points }) {
  if (!points || points.length === 0) {
    return (
      <div className="empty-state">Chưa có dữ liệu để vẽ biểu đồ xu hướng giá.</div>
    );
  }

  const width = 720;
  const height = 260;
  const padding = { top: 16, right: 24, bottom: 36, left: 70 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const values = points.map((p) => p.gia_trung_binh);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue || 1;

  const stepX = points.length > 1 ? innerWidth / (points.length - 1) : 0;

  const coords = points.map((p, i) => {
    const x = padding.left + (points.length > 1 ? i * stepX : innerWidth / 2);
    const y =
      padding.top + innerHeight - ((p.gia_trung_binh - minValue) / valueRange) * innerHeight;
    return { x, y, point: p };
  });

  const pathD = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto" }}>
      {/* Trục Y — 4 mốc tham chiếu */}
      {[0, 1, 2, 3, 4].map((i) => {
        const y = padding.top + (innerHeight / 4) * i;
        const value = maxValue - (valueRange / 4) * i;
        return (
          <g key={i}>
            <line
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              stroke="#e5e7eb"
              strokeWidth={1}
            />
            <text x={padding.left - 8} y={y + 4} fontSize={10} textAnchor="end" fill="#666">
              {Math.round(value).toLocaleString("vi-VN")}
            </text>
          </g>
        );
      })}

      {/* Đường xu hướng */}
      <path d={pathD} fill="none" stroke="#2563eb" strokeWidth={2} />

      {/* Điểm dữ liệu + nhãn kỳ */}
      {coords.map((c, i) => (
        <g key={i}>
          <circle cx={c.x} cy={c.y} r={3.5} fill="#2563eb" />
          <title>
            {c.point.ky}: {c.point.gia_trung_binh.toLocaleString("vi-VN")} (
            {c.point.so_ban_ghi} bản ghi)
          </title>
          <text
            x={c.x}
            y={height - padding.bottom + 16}
            fontSize={10}
            textAnchor="middle"
            fill="#666"
          >
            {c.point.ky}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function PriceDataPage() {
  const [matHang, setMatHang] = useState("");
  const [diaBan, setDiaBan] = useState("");
  const [kyFrom, setKyFrom] = useState("");
  const [kyTo, setKyTo] = useState("");
  const [page, setPage] = useState(1);

  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [trend, setTrend] = useState({ points: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  // ---------- Bước 1-2: Nhập bộ lọc (mặt hàng, địa bàn, kỳ) -> Hệ thống
  // truy vấn curated.dm_gia -> Hiển thị giá theo bảng ----------
  async function runQuery(nextPage = 1) {
    setLoading(true);
    setError(null);
    try {
      const [page_data, trend_data] = await Promise.all([
        searchPriceData({ matHang, diaBan, kyFrom, kyTo, page: nextPage, pageSize: PAGE_SIZE }),
        getPriceTrend({ matHang, diaBan, kyFrom, kyTo }),
      ]);
      setResult(page_data);
      setTrend(trend_data);
      setPage(nextPage);
      setSearched(true);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runQuery(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    runQuery(1);
  }

  const totalPages = Math.max(1, Math.ceil(result.total / result.page_size));

  return (
    <AppLayout
      title="Tra cứu dữ liệu giá"
      subtitle="UC-055 — Nhập bộ lọc (mặt hàng, địa bàn, kỳ), hệ thống truy vấn curated.dm_gia, hiển thị giá theo bảng + biểu đồ xu hướng giá theo thời gian."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Bước 1 — Nhập bộ lọc (mặt hàng, địa bàn, kỳ) */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Search size={16} /> Bộ lọc tra cứu giá
          </h3>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="field">
                <label>Mặt hàng</label>
                <input
                  type="text"
                  placeholder="Vd: Gạo ST25, GAO-ST25..."
                  value={matHang}
                  onChange={(e) => setMatHang(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Địa bàn</label>
                <input
                  type="text"
                  placeholder="Vd: TP. Hà Nội, HN..."
                  value={diaBan}
                  onChange={(e) => setDiaBan(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Kỳ từ (YYYY-MM)</label>
                <input
                  type="month"
                  value={kyFrom}
                  onChange={(e) => setKyFrom(e.target.value)}
                />
              </div>
              <div className="field">
                <label>đến kỳ (YYYY-MM)</label>
                <input type="month" value={kyTo} onChange={(e) => setKyTo(e.target.value)} />
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

      {/* Bước 3-4 — Biểu đồ xu hướng giá theo thời gian (line chart) */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <LineChart size={16} /> Xu hướng giá theo thời gian
          </h3>
        </div>
        <div className="card-body">
          {loading ? (
            <p style={{ color: "#666" }}>Đang tải biểu đồ...</p>
          ) : (
            <PriceTrendChart points={trend.points} />
          )}
        </div>
      </div>

      {/* Bước 2 — Hiển thị giá theo bảng */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            Bảng giá chi tiết
          </h3>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => runQuery(page)}
            disabled={loading}
          >
            <RefreshCw size={14} /> Tải lại
          </button>
        </div>
        <div className="card-body">
          {loading ? (
            <p style={{ color: "#666" }}>Đang tra cứu...</p>
          ) : searched && result.items.length === 0 ? (
            <div className="empty-state">Không tìm thấy dữ liệu giá nào phù hợp bộ lọc.</div>
          ) : result.items.length > 0 ? (
            <>
              <p style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                Tìm thấy {result.total} bản ghi — trang {result.page}/{totalPages}
              </p>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mặt hàng</th>
                      <th>Địa bàn</th>
                      <th>Kỳ</th>
                      <th>Giá</th>
                      <th>Đơn vị tính</th>
                      <th>Nguồn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {row.mat_hang_name}{" "}
                          <span style={{ color: "#999", fontSize: 11 }}>
                            ({row.mat_hang_code})
                          </span>
                        </td>
                        <td>
                          {row.dia_ban_name}{" "}
                          <span style={{ color: "#999", fontSize: 11 }}>
                            ({row.dia_ban_code})
                          </span>
                        </td>
                        <td>{row.ky}</td>
                        <td>{row.gia.toLocaleString("vi-VN")}</td>
                        <td>{row.don_vi_tinh}</td>
                        <td>{row.nguon}</td>
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
                  onClick={() => runQuery(page - 1)}
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
                  onClick={() => runQuery(page + 1)}
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