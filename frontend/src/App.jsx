import { Route, Routes } from "react-router-dom";
import { ArrowRight, Building2, KeyRound, Settings, UserCog, Users } from "lucide-react";
import { Link } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import IntegrationConfigPage from "./pages/IntegrationConfigPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotificationChannelsPage from "./pages/NotificationChannelsPage.jsx";
import OrgUnitsPage from "./pages/OrgUnitsPage.jsx";
import PermissionsPage from "./pages/PermissionsPage.jsx";
import RolesPage from "./pages/RolesPage.jsx";
import SystemConfigPage from "./pages/SystemConfigPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";

function HomePage() {
  const modules = [
    {
      to: "/org-units",
      title: "Cơ cấu tổ chức",
      description: "UC-01 — Quản lý danh mục đơn vị (Sở / Phòng / Xã) dạng cây.",
      icon: Building2,
    },
    {
      to: "/users",
      title: "Người dùng",
      description: "UC-02 — Quản lý tài khoản người dùng, gán đơn vị công tác.",
      icon: Users,
    },
    {
      to: "/permissions",
      title: "Quyền người dùng",
      description: "UC-04 — Xem/cấu hình permission_context: vai trò, miền dữ liệu, mức nhạy cảm.",
      icon: KeyRound,
    },
    {
      to: "/roles",
      title: "Vai trò người dùng",
      description: "UC-05 — Quản lý danh mục vai trò và bộ quyền gán cho từng vai trò.",
      icon: UserCog,
    },
    {
      to: "/system-config",
      title: "Cấu hình hệ thống chung",
      description: "UC-06 — Thời gian chờ, dung lượng tải lên tối đa, ngôn ngữ mặc định.",
      icon: Settings,
    },
  ];

  return (
    <AppLayout
      title="Tổng quan"
      subtitle="Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Tỉnh Hưng Yên. Các module hoàn thành theo PLAN.md."
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 16,
        }}
      >
        {modules.map((m) => {
          const Icon = m.icon;
          return (
            <Link
              key={m.to}
              to={m.to}
              className="card"
              style={{ padding: 20, textDecoration: "none", color: "inherit" }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: "var(--color-primary-soft)",
                  color: "var(--color-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 14,
                }}
              >
                <Icon size={20} />
              </div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.title}</div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                {m.description}
              </div>
              <div
                style={{
                  marginTop: 14,
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--color-primary)",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                Mở module <ArrowRight size={14} />
              </div>
            </Link>
          );
        })}
      </div>
    </AppLayout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org-units"
        element={
          <ProtectedRoute>
            <OrgUnitsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute>
            <UsersPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/permissions"
        element={
          <ProtectedRoute>
            <PermissionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/roles"
        element={
          <ProtectedRoute>
            <RolesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/system-config"
        element={
          <ProtectedRoute>
            <SystemConfigPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/integration-config"
        element={
          <ProtectedRoute>
            <IntegrationConfigPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notification-channels"
        element={
          <ProtectedRoute>
            <NotificationChannelsPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}