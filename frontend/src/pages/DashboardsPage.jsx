import { useEffect, useState } from "react";
import { LayoutDashboard, Pin, PinOff, RefreshCw, Star } from "lucide-react";
import { Link } from "react-router-dom";
import AppLayout from "../components/AppLayout.jsx";
import DataFreshnessPanel from "../components/DataFreshnessPanel.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  listDashboards,
  listFavoriteDashboards,
  pinFavoriteDashboard,
  unpinFavoriteDashboard,
} from "../api/dashboards.js";

const CATEGORY_LABELS = {
  NGAN_SACH: "Ngân sách",
  TAI_SAN_CONG: "Tài sản công",
  DAU_TU_CONG: "Đầu tư công",
  GIA: "Giá",
  TONG_HOP: "Tổng hợp",
};

export default function DashboardsPage() {
  const { user } = useAuth();
  const userId = user?.id;

  const [categoryFilter, setCategoryFilter] = useState("");
  const [dashboards, setDashboards] = useState([]);
  const [favoriteIds, setFavoriteIds] = useState(new Set());

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [pinningId, setPinningId] = useState(null);

  // ---------- Bước 1: Chọn Bảng điều khiển từ danh mục -> hệ thống hiển thị danh sách ----------
  async function loadCatalog() {
    setLoading(true);
    try {
      const [catalog, favorites] = await Promise.all([
        listDashboards({ onlyActive: true, category: categoryFilter || null }),
        userId ? listFavoriteDashboards(userId) : Promise.resolve([]),
      ]);
      setDashboards(catalog);
      setFavoriteIds(new Set(favorites.map((d) => d.id)));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryFilter, userId]);

  // ---------- Bước 3: Ghim/bỏ ghim bảng điều khiển yêu thích -> lưu vào tùy chọn cá nhân ----------
  async function togglePin(dashboard) {
    if (!userId) {
      setError("Không xác định được người dùng hiện tại — vui lòng đăng nhập lại.");
      return;
    }
    setPinningId(dashboard.id);
    setError(null);
    setInfo(null);
    try {
      if (favoriteIds.has(dashboard.id)) {
        await unpinFavoriteDashboard(dashboard.id, userId);
        setFavoriteIds((prev) => {
          const next = new Set(prev);
          next.delete(dashboard.id);
          return next;
        });
        setInfo(`Đã bỏ ghim "${dashboard.name}" khỏi mục yêu thích.`);
      } else {
        await pinFavoriteDashboard(dashboard.id, userId);
        setFavoriteIds((prev) => new Set(prev).add(dashboard.id));
        setInfo(`Đã ghim "${dashboard.name}" vào mục yêu thích.`);
      }
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setPinningId(null);
    }
  }

  const favoriteDashboards = dashboards.filter((d) => favoriteIds.has(d.id));
  const otherDashboards = dashboards.filter((d) => !favoriteIds.has(d.id));

  return (
    <AppLayout
      title="Bảng điều khiển"
      subtitle="UC-047 — Xem Bảng điều khiển điều hành. Chọn 1 bảng điều khiển từ danh mục để xem trực tiếp từ Superset, hoặc ghim bảng điều khiển yêu thích vào tùy chọn cá nhân. UC-057 — Xem ô thông tin độ mới dữ liệu + bảng chi tiết last_sync/độ đầy đủ theo nguồn."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}
      {info && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          {info}
        </div>
      )}

      {/* UC-057 — Hiển thị độ mới dữ liệu (ô tổng quan + bảng chi tiết theo nguồn) */}
      <DataFreshnessPanel />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3>Danh mục Bảng điều khiển</h3>
        </div>
        <div className="card-body">
          <div className="form-grid" style={{ marginBottom: 16 }}>
            <div className="field">
              <label>Lĩnh vực</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">Tất cả lĩnh vực</option>
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ justifyContent: "flex-end" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={loadCatalog}
                disabled={loading}
              >
                <RefreshCw size={14} /> Tải lại
              </button>
            </div>
          </div>

          {favoriteDashboards.length > 0 && (
            <>
              <h4 style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                <Star size={16} /> Đã ghim yêu thích
              </h4>
              <DashboardGrid
                dashboards={favoriteDashboards}
                favoriteIds={favoriteIds}
                onTogglePin={togglePin}
                pinningId={pinningId}
              />
              <div style={{ height: 20 }} />
            </>
          )}

          <h4 style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <LayoutDashboard size={16} /> Toàn bộ danh mục
          </h4>
          {loading && dashboards.length === 0 ? (
            <p style={{ color: "#666" }}>Đang tải...</p>
          ) : otherDashboards.length === 0 && favoriteDashboards.length === 0 ? (
            <div className="empty-state">Chưa có Bảng điều khiển nào trong danh mục.</div>
          ) : (
            <DashboardGrid
              dashboards={otherDashboards}
              favoriteIds={favoriteIds}
              onTogglePin={togglePin}
              pinningId={pinningId}
            />
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function DashboardGrid({ dashboards, favoriteIds, onTogglePin, pinningId }) {
  if (dashboards.length === 0) return null;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        gap: 14,
      }}
    >
      {dashboards.map((d) => {
        const isFavorite = favoriteIds.has(d.id);
        return (
          <div
            key={d.id}
            className="card"
            style={{ margin: 0, display: "flex", flexDirection: "column" }}
          >
            <div className="card-body" style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 8,
                }}
              >
                <div>
                  <span className="badge" style={{ marginBottom: 6 }}>
                    {CATEGORY_LABELS[d.category] || d.category}
                  </span>
                  <h4 style={{ margin: "4px 0" }}>{d.name}</h4>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  title={isFavorite ? "Bỏ ghim yêu thích" : "Ghim yêu thích"}
                  onClick={() => onTogglePin(d)}
                  disabled={pinningId === d.id}
                  style={{ padding: "6px 8px" }}
                >
                  {isFavorite ? <PinOff size={14} /> : <Pin size={14} />}
                </button>
              </div>
              <p style={{ color: "#666", fontSize: 13, minHeight: 36 }}>{d.description}</p>
              <Link to={`/dashboards/${d.id}`} className="btn btn-primary" style={{ width: "100%" }}>
                Xem Bảng điều khiển
              </Link>
            </div>
          </div>
        );
      })}
    </div>
  );
}