import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Pin, PinOff } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  getDashboard,
  getDashboardGuestToken,
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

export default function DashboardDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const userId = user?.id;

  const [dashboard, setDashboard] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(true);
  const [embedding, setEmbedding] = useState(true);
  const [pinning, setPinning] = useState(false);
  const [error, setError] = useState(null);

  const mountRef = useRef(null);
  const embeddedRef = useRef(null);

  // ---------- Bước 2 (nâng cấp Embedded SDK): Xem Bảng điều khiển ----------
  // Không còn nhúng <iframe src={embed_url}> trực tiếp — dùng
  // @superset-ui/embedded-sdk + Guest Token (JWT ngắn hạn, kèm RLS theo
  // người dùng), là cách chính thức Superset hỗ trợ để kiểm soát quyền
  // khi nhúng dashboard.
  async function load() {
    setLoading(true);
    try {
      const [detail, favorites] = await Promise.all([
        getDashboard(id),
        userId ? listFavoriteDashboards(userId) : Promise.resolve([]),
      ]);
      setDashboard(detail);
      setIsFavorite(favorites.some((f) => f.id === detail.id));
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, userId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchGuestToken() {
      // Gọi lại backend MỖI lần SDK cần token mới (kể cả lúc tự làm mới
      // trước khi token cũ hết hạn) — không cache lâu dài phía frontend,
      // để RLS luôn phản ánh đúng quyền hiện tại của người dùng.
      const { guest_token: guestToken } = await getDashboardGuestToken(dashboard.id, {
        userId,
        username: user?.username,
        fullName: user?.full_name,
      });
      return guestToken;
    }

    async function mountEmbeddedDashboard() {
      if (!dashboard || !userId || !mountRef.current) return;
      setEmbedding(true);
      try {
        // Lấy 1 lượt trước để biết superset_domain (do backend cấu hình,
        // không hard-code ở frontend) trước khi gọi embedDashboard().
        const first = await getDashboardGuestToken(dashboard.id, {
          userId,
          username: user?.username,
          fullName: user?.full_name,
        });
        if (cancelled || !mountRef.current) return;

        const { embedDashboard } = await import("@superset-ui/embedded-sdk");
        if (cancelled || !mountRef.current) return;

        mountRef.current.innerHTML = "";
        embeddedRef.current = await embedDashboard({
          id: first.superset_dashboard_uid,
          supersetDomain: first.superset_domain,
          mountPoint: mountRef.current,
          fetchGuestToken,
          dashboardUiConfig: {
            hideTitle: true,
            hideChartControls: false,
            hideTab: false,
          },
        });
        if (!cancelled) setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(
            e?.response?.data?.detail?.message ||
              e.message ||
              "Không nhúng được Bảng điều khiển từ Superset"
          );
        }
      } finally {
        if (!cancelled) setEmbedding(false);
      }
    }

    mountEmbeddedDashboard();
    return () => {
      cancelled = true;
      try {
        embeddedRef.current?.unmount?.();
      } catch {
        // ignore lỗi unmount khi component đã rời trang
      }
      if (mountRef.current) mountRef.current.innerHTML = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.id, userId]);

  // ---------- Bước 3: Ghim/bỏ ghim bảng điều khiển yêu thích ----------
  async function togglePin() {
    if (!userId || !dashboard) return;
    setPinning(true);
    setError(null);
    try {
      if (isFavorite) {
        await unpinFavoriteDashboard(dashboard.id, userId);
        setIsFavorite(false);
      } else {
        await pinFavoriteDashboard(dashboard.id, userId);
        setIsFavorite(true);
      }
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setPinning(false);
    }
  }

  return (
    <AppLayout
      title={dashboard ? dashboard.name : "Bảng điều khiển"}
      subtitle="UC-047 — Xem Bảng điều khiển điều hành (hiển thị trực tiếp từ Superset)."
    >
      <Link
        to="/dashboards"
        className="btn btn-secondary"
        style={{ marginBottom: 12, display: "inline-flex" }}
      >
        <ArrowLeft size={14} /> Quay lại danh mục
      </Link>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading && <p style={{ color: "#666" }}>Đang tải...</p>}

      {!loading && dashboard && (
        <div className="card">
          <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span className="badge" style={{ marginBottom: 4 }}>
                {CATEGORY_LABELS[dashboard.category] || dashboard.category}
              </span>
              <h3 style={{ margin: "4px 0" }}>{dashboard.name}</h3>
              <p style={{ color: "#666", fontSize: 13, margin: 0 }}>{dashboard.description}</p>
            </div>
            <button
              type="button"
              className={isFavorite ? "btn btn-secondary" : "btn btn-primary"}
              onClick={togglePin}
              disabled={pinning || !userId}
            >
              {isFavorite ? (
                <>
                  <PinOff size={14} /> Bỏ ghim yêu thích
                </>
              ) : (
                <>
                  <Pin size={14} /> Ghim yêu thích
                </>
              )}
            </button>
          </div>
          <div className="card-body">
            {/* UC-047 (nâng cấp): nhúng qua @superset-ui/embedded-sdk +
                Guest Token thay cho <iframe src={embed_url}> tĩnh — kiểm
                soát được quyền xem theo từng người dùng (RLS). */}
            {embedding && <p style={{ color: "#666" }}>Đang tải Bảng điều khiển từ Superset...</p>}
            {!userId && (
              <div className="alert alert-error">
                Không xác định được người dùng hiện tại — không thể phát hành
                Guest Token để nhúng Bảng điều khiển.
              </div>
            )}
            <div
              ref={mountRef}
              style={{
                width: "100%",
                minHeight: "75vh",
                border: "1px solid #e2e2e2",
                borderRadius: 8,
                display: embedding ? "none" : "block",
              }}
            />
          </div>
        </div>
      )}
    </AppLayout>
  );
}