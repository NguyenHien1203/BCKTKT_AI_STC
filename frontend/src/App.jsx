import { Route, Routes } from "react-router-dom";
import { ArrowRight, Building2, Users } from "lucide-react";
import { Link } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import OrgUnitsPage from "./pages/OrgUnitsPage.jsx";
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
    </Routes>
  );
}
