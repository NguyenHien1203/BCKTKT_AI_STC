import { NavLink, useNavigate } from "react-router-dom";
import { KeyRound, LogOut } from "lucide-react";
import { NAV_SECTIONS } from "../nav.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function AppLayout({ title, subtitle, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Kho Dữ Liệu Tài Chính
          <span>Tỉnh Hưng Yên</span>
        </div>

        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <div className="sidebar-group-label">{section.label}</div>
            {section.items.map((item) => {
              const Icon = item.icon;
              if (item.disabled) {
                return (
                  <div
                    key={item.to}
                    className="nav-link"
                    style={{ opacity: 0.45, cursor: "not-allowed" }}
                    title="Chưa triển khai"
                  >
                    <Icon size={17} strokeWidth={2} />
                    {item.label}
                  </div>
                );
              }
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                >
                  <Icon size={17} strokeWidth={2} />
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        ))}
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">{title}</div>
          {user && (
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{user.full_name}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                  {user.role}
                </div>
              </div>
              <NavLink className="icon-btn" title="Đổi mật khẩu" to="/change-password">
                <KeyRound size={15} />
              </NavLink>
              <button className="icon-btn" title="Đăng xuất" onClick={handleLogout}>
                <LogOut size={15} />
              </button>
            </div>
          )}
        </header>
        <main className="page-content">
          {subtitle && (
            <div className="page-header">
              <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
              </div>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}