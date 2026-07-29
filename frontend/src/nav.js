import {
  Bell,
  Building2,
  Database,
  FileStack,
  LayoutDashboard,
  MonitorSmartphone,
  Network,
  Plug,
  PlugZap,
  ScanSearch,
  Settings,
  ShieldCheck,
  Sparkles,
  Wrench,
  Users,
  FileBarChart,
  FileText,
  KeyRound,
  UserCog,
} from "lucide-react";

// Mỗi mục tương ứng 1 UC/nhóm UC đã có giao diện. Khi thêm UC mới có màn hình,
// bổ sung vào đây theo đúng nhóm nghiệp vụ (xem ARCHITECTURE.md mục 2).
export const NAV_SECTIONS = [
  {
    label: "Quản trị hệ thống",
    items: [
      { to: "/org-units", label: "Cơ cấu tổ chức", icon: Building2 },
      { to: "/users", label: "Người dùng", icon: Users },
      { to: "/permissions", label: "Quyền người dùng", icon: KeyRound },
      { to: "/roles", label: "Vai trò người dùng", icon: UserCog },
      { to: "/system-config", label: "Cấu hình hệ thống chung", icon: Settings },
      { to: "/integration-config", label: "Cấu hình tích hợp", icon: Network },
      { to: "/notification-channels", label: "Cấu hình kênh thông báo", icon: Bell },
      { to: "/audit-logs", label: "Nhật ký truy cập và thao tác", icon: FileText },
      { to: "/ai-audit-logs", label: "Quản trị AI Audit Log", icon: ScanSearch },
      { to: "/guide-documents", label: "Tài liệu hướng dẫn sử dụng", icon: FileStack },
      { to: "/sessions", label: "Quản lý phiên đăng nhập", icon: MonitorSmartphone },
    ],
  },
  {
    label: "Dữ liệu",
    items: [
      { to: "/data-sources", label: "Nguồn dữ liệu", icon: Database },
      { to: "/connectors", label: "Thư viện bộ kết nối", icon: Plug },
      { to: "/source-connections", label: "Cấu hình kết nối nguồn", icon: PlugZap },
      { to: "/data-quality", label: "Chuẩn hoá dữ liệu", icon: ShieldCheck, disabled: true },
    ],
  },
  {
    label: "Khai thác",
    items: [
      { to: "/dashboard", label: "Bảng điều khiển", icon: LayoutDashboard, disabled: true },
      { to: "/reports", label: "Báo cáo", icon: FileBarChart, disabled: true },
    ],
  },
  {
    label: "Nền tảng",
    items: [
      { to: "/integrations", label: "API & tích hợp", icon: Network, disabled: true },
      { to: "/ai", label: "Trợ lý AI", icon: Sparkles, disabled: true },
      { to: "/ops", label: "Vận hành", icon: Wrench, disabled: true },
    ],
  },
];