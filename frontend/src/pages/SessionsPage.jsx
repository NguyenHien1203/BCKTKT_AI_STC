import { useEffect, useState } from "react";
import { AlertCircle, Filter, LogOut, RotateCcw, ShieldOff } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import { listSessions, revokeSession } from "../api/sessions.js";
import { listUsers } from "../api/users.js";

const EMPTY_FILTERS = { userId: "", onlyActive: true };

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

export default function SessionsPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function reload(activeFilters = filters) {
    setLoading(true);
    try {
      const data = await listSessions({
        userId: activeFilters.userId ? Number(activeFilters.userId) : undefined,
        onlyActive: activeFilters.onlyActive,
      });
      setSessions(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload(EMPTY_FILTERS);
    listUsers().then(setUsers).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(e) {
    e.preventDefault();
    reload(filters);
  }

  function handleResetFilters() {
    setFilters(EMPTY_FILTERS);
    reload(EMPTY_FILTERS);
  }

  async function handleRevoke(session) {
    if (
      !window.confirm(
        `Thu hồi phiên đăng nhập của "${session.full_name}" (${session.username})?`
      )
    ) {
      return;
    }
    try {
      await revokeSession(session.id);
      await reload();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Quản lý phiên đăng nhập"
      subtitle="UC-14 — Xem và thu hồi từng phiên đăng nhập đang hoạt động trong hệ thống."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body">
          <form onSubmit={handleFilterSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="userId">Người dùng</label>
                <select
                  id="userId"
                  value={filters.userId}
                  onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
                >
                  <option value="">Tất cả người dùng</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.username})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="onlyActive">Trạng thái</label>
                <select
                  id="onlyActive"
                  value={filters.onlyActive ? "active" : "all"}
                  onChange={(e) =>
                    setFilters({ ...filters, onlyActive: e.target.value === "active" })
                  }
                >
                  <option value="active">Đang hoạt động</option>
                  <option value="all">Tất cả (kể cả đã thu hồi)</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">
                <Filter size={15} />
                Lọc
              </button>
              <button type="button" className="btn btn-secondary" onClick={handleResetFilters}>
                <RotateCcw size={15} />
                Đặt lại
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Danh sách phiên đăng nhập ({sessions.length})</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : sessions.length === 0 ? (
            <div className="empty-state">Không có phiên đăng nhập nào phù hợp bộ lọc.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Người dùng</th>
                  <th>Tên đăng nhập</th>
                  <th>Token</th>
                  <th>Thời điểm đăng nhập</th>
                  <th>Trạng thái</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{s.full_name}</td>
                    <td>{s.username}</td>
                    <td>
                      <code style={{ fontSize: 12 }}>{s.token_preview}</code>
                    </td>
                    <td>{formatTime(s.created_at)}</td>
                    <td>
                      <span className={`badge ${s.is_revoked ? "badge-neutral" : "badge-success"}`}>
                        {s.is_revoked ? "Đã thu hồi" : "Đang hoạt động"}
                      </span>
                    </td>
                    <td>
                      {!s.is_revoked && (
                        <div className="row-actions">
                          <button
                            className="icon-btn"
                            title="Thu hồi phiên"
                            onClick={() => handleRevoke(s)}
                          >
                            <LogOut size={15} />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div
        style={{
          marginTop: 14,
          fontSize: 12,
          color: "var(--color-text-secondary)",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <ShieldOff size={13} />
        Thu hồi 1 phiên chỉ đăng xuất đúng thiết bị/phiên đó. Để buộc đăng xuất toàn bộ phiên của
        1 người dùng, dùng hành động "Buộc đăng xuất" ở trang Người dùng (UC-03).
      </div>
    </AppLayout>
  );
}