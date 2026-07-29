import { Route, Routes } from "react-router-dom";
import { ArrowRight, Building2, Database, FileStack, FileText, KeyRound, MonitorSmartphone, Plug, PlugZap, ScanSearch, Settings, UserCog, Users } from "lucide-react";
import { Link } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AiAuditLogPage from "./pages/AiAuditLogPage.jsx";
import AuditLogsPage from "./pages/AuditLogsPage.jsx";
import ChangePasswordPage from "./pages/ChangePasswordPage.jsx";
import ConnectorsPage from "./pages/ingestion/ConnectorsPage.jsx";
import DataSourcesPage from "./pages/ingestion/DataSourcesPage.jsx";
import SourceConnectionsPage from "./pages/ingestion/SourceConnectionsPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import GuideDocumentsPage from "./pages/GuideDocumentsPage.jsx";
import IntegrationConfigPage from "./pages/IntegrationConfigPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotificationChannelsPage from "./pages/NotificationChannelsPage.jsx";
import OrgUnitsPage from "./pages/OrgUnitsPage.jsx";
import PermissionsPage from "./pages/PermissionsPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";
import RolesPage from "./pages/RolesPage.jsx";
import SessionsPage from "./pages/SessionsPage.jsx";
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
    {
      to: "/audit-logs",
      title: "Nhật ký truy cập và thao tác",
      description: "UC-09 — Xem/lọc nhật ký theo tài khoản, thời gian; xuất báo cáo ATTT định kỳ (PDF).",
      icon: FileText,
    },
    {
      to: "/ai-audit-logs",
      title: "Quản trị AI Audit Log",
      description: "UC-10 — Xem AI query theo thời gian/trace_id/user_id; xuất báo cáo AI Audit định kỳ (PDF).",
      icon: ScanSearch,
    },
    {
      to: "/guide-documents",
      title: "Tài liệu hướng dẫn sử dụng",
      description: "UC-11 — Thêm/sửa/xoá tài liệu hướng dẫn (lưu MinIO, quản lý phiên bản, xoá mềm).",
      icon: FileStack,
    },
    {
      to: "/sessions",
      title: "Quản lý phiên đăng nhập",
      description: "UC-14 — Xem và thu hồi từng phiên đăng nhập đang hoạt động trong hệ thống.",
      icon: MonitorSmartphone,
    },
    {
      to: "/data-sources",
      title: "Nguồn dữ liệu",
      description: "UC-015 — Đăng ký, xem, sửa và vô hiệu hoá nguồn dữ liệu (TABMIS, QLVBĐH, MISA, QL Giá, PMSTT).",
      icon: Database,
    },
    {
      to: "/connectors",
      title: "Thư viện bộ kết nối",
      description: "UC-016 — Xem danh sách, đăng ký (plugin) và cập nhật phiên bản bộ kết nối (tệp/REST API/JDBC/SOAP).",
      icon: Plug,
    },
    {
      to: "/source-connections",
      title: "Cấu hình kết nối nguồn",
      description: "UC-017 — Cấu hình connection (API/DB/File), kiểm thử kết nối, quản lý certificate/API key và cảnh báo hết hạn.",
      icon: PlugZap,
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
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePasswordPage />
          </ProtectedRoute>
        }
      />
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
      <Route
        path="/audit-logs"
        element={
          <ProtectedRoute>
            <AuditLogsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ai-audit-logs"
        element={
          <ProtectedRoute>
            <AiAuditLogPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/guide-documents"
        element={
          <ProtectedRoute>
            <GuideDocumentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sessions"
        element={
          <ProtectedRoute>
            <SessionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/data-sources"
        element={
          <ProtectedRoute>
            <DataSourcesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/connectors"
        element={
          <ProtectedRoute>
            <ConnectorsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/source-connections"
        element={
          <ProtectedRoute>
            <SourceConnectionsPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}