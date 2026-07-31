import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, KeyRound, LogOut } from "lucide-react";
import { NAV_SECTIONS } from "../nav.js";
import { useAuth } from "../context/AuthContext.jsx";

function sectionHasActiveItem(section, pathname) {
  return section.items.some((item) => pathname.startsWith(item.to));
}

export default function AppLayout({ title, subtitle, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Mặc định: mở sẵn nhóm menu chứa trang đang xem, thu gọn các nhóm còn lại.
  const [openSections, setOpenSections] = useState(() => {
    const initial = {};
    NAV_SECTIONS.forEach((section) => {
      initial[section.label] = sectionHasActiveItem(section, location.pathname);
    });
    return initial;
  });

  // Nếu điều hướng tới 1 trang thuộc nhóm đang thu gọn (vd bấm link ở nơi
  // khác), tự mở nhóm đó ra để người dùng luôn thấy menu đang active.
  useEffect(() => {
    setOpenSections((prev) => {
      let changed = false;
      const next = { ...prev };
      NAV_SECTIONS.forEach((section) => {
        if (sectionHasActiveItem(section, location.pathname) && !next[section.label]) {
          next[section.label] = true;
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [location.pathname]);

  function toggleSection(label) {
    setOpenSections((prev) => {
      const willOpen = !prev[label];
      if (willOpen) {
        // Khi mở 1 menu, nhảy lên đầu trang để người dùng thấy toàn bộ menu vừa mở.
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      return { ...prev, [label]: willOpen };
    });
  }

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

        {NAV_SECTIONS.map((section) => {
          const isOpen = !!openSections[section.label];
          const isActiveGroup = sectionHasActiveItem(section, location.pathname);
          return (
            <div key={section.label} className="sidebar-group">
              <button
                type="button"
                className={`sidebar-group-label${isActiveGroup ? " active-group" : ""}`}
                onClick={() => toggleSection(section.label)}
                aria-expanded={isOpen}
              >
                <span>{section.label}</span>
                {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
              {isOpen && (
                <div className="sidebar-group-items">
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
              )}
            </div>
          );
        })}
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