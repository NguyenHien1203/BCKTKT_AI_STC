import {
  Building2,
  Database,
  LayoutDashboard,
  Network,
  ShieldCheck,
  Sparkles,
  Wrench,
  Users,
  FileBarChart,
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
    ],
  },
  {
    label: "Dữ liệu",
    items: [
      { to: "/ingestion", label: "Tiếp nhận dữ liệu", icon: Database, disabled: true },
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