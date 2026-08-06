import { Route, Routes } from "react-router-dom";
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  CalendarClock,
  ClipboardCheck,
  Database,
  FileScan,
  FileStack,
  FlaskConical,
  FileText,
  FileUp,
  Gauge,
  History,
  Inbox,
  KeyRound,
  Landmark,
  Layers,
  MonitorSmartphone,
  Network,
  Package,
  Percent,
  BookCopy,
  CloudUpload,
  Plug,
  PlugZap,
  RefreshCw,
  ScanSearch,
  Settings,
  ShieldAlert,
  Tag,
  Ticket,
  UploadCloud,
  UserCog,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AiAuditLogPage from "./pages/AiAuditLogPage.jsx";
import AuditLogsPage from "./pages/AuditLogsPage.jsx";
import ChangePasswordPage from "./pages/ChangePasswordPage.jsx";
import ConnectorsPage from "./pages/ingestion/ConnectorsPage.jsx";
import DataSourcesPage from "./pages/ingestion/DataSourcesPage.jsx";
import DatasetsPage from "./pages/ingestion/DatasetsPage.jsx";
import IncrementalSyncPage from "./pages/ingestion/IncrementalSyncPage.jsx";
import IngestionRunsPage from "./pages/ingestion/IngestionRunsPage.jsx";
import IntakeReconciliationPage from "./pages/ingestion/IntakeReconciliationPage.jsx";
import ReconciliationTicketPage from "./pages/ingestion/ReconciliationTicketPage.jsx";
import ScheduledTasksPage from "./pages/ingestion/ScheduledTasksPage.jsx";
import SchemaRegistryChecksPage from "./pages/ingestion/SchemaRegistryChecksPage.jsx";
import SourceConnectionsPage from "./pages/ingestion/SourceConnectionsPage.jsx";
import TabmisIntakePage from "./pages/ingestion/TabmisIntakePage.jsx";
import TabmisIntakeDetailPage from "./pages/ingestion/TabmisIntakeDetailPage.jsx";
import VanBanIntakePage from "./pages/ingestion/VanBanIntakePage.jsx";
import ParsingJobsPage from "./pages/dataquality/ParsingJobsPage.jsx";
import MappingJobsPage from "./pages/dataquality/MappingJobsPage.jsx";
import OcrJobsPage from "./pages/dataquality/OcrJobsPage.jsx";
import UnmappedQueuePage from "./pages/dataquality/UnmappedQueuePage.jsx";
import OrgUnitCatalogPage from "./pages/dataquality/OrgUnitCatalogPage.jsx";
import BudgetItemCatalogPage from "./pages/dataquality/BudgetItemCatalogPage.jsx";
import AssetGroupCatalogPage from "./pages/dataquality/AssetGroupCatalogPage.jsx";
import CatalogChangeApprovalsPage from "./pages/dataquality/CatalogChangeApprovalsPage.jsx";
import CatalogEntriesPage from "./pages/dataquality/CatalogEntriesPage.jsx";
import QualityRulesPage from "./pages/dataquality/QualityRulesPage.jsx";
import QualityChecksPage from "./pages/dataquality/QualityChecksPage.jsx";
import QualityExceptionsPage from "./pages/dataquality/QualityExceptionsPage.jsx";
import CuratedPublishPage from "./pages/dataquality/CuratedPublishPage.jsx";
import DatasetMetadataPage from "./pages/dataquality/DatasetMetadataPage.jsx";
import SemanticIndicatorsPage from "./pages/dataquality/SemanticIndicatorsPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import GuideDocumentsPage from "./pages/GuideDocumentsPage.jsx";
import IntegrationConfigPage from "./pages/IntegrationConfigPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import OidcCallbackPage from "./pages/OidcCallbackPage.jsx";
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
      description:
        "UC-01 — Quản lý danh mục đơn vị (Sở / Phòng / Xã) dạng cây.",
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
      description:
        "UC-04 — Xem/cấu hình permission_context: vai trò, miền dữ liệu, mức nhạy cảm.",
      icon: KeyRound,
    },
    {
      to: "/roles",
      title: "Vai trò người dùng",
      description:
        "UC-05 — Quản lý danh mục vai trò và bộ quyền gán cho từng vai trò.",
      icon: UserCog,
    },
    {
      to: "/system-config",
      title: "Cấu hình hệ thống chung",
      description:
        "UC-06 — Thời gian chờ, dung lượng tải lên tối đa, ngôn ngữ mặc định.",
      icon: Settings,
    },
    {
      to: "/audit-logs",
      title: "Nhật ký truy cập và thao tác",
      description:
        "UC-09 — Xem/lọc nhật ký theo tài khoản, thời gian; xuất báo cáo ATTT định kỳ (PDF).",
      icon: FileText,
    },
    {
      to: "/ai-audit-logs",
      title: "Quản trị AI Audit Log",
      description:
        "UC-10 — Xem AI query theo thời gian/trace_id/user_id; xuất báo cáo AI Audit định kỳ (PDF).",
      icon: ScanSearch,
    },
    {
      to: "/guide-documents",
      title: "Tài liệu hướng dẫn sử dụng",
      description:
        "UC-11 — Thêm/sửa/xoá tài liệu hướng dẫn (lưu MinIO, quản lý phiên bản, xoá mềm).",
      icon: FileStack,
    },
    {
      to: "/sessions",
      title: "Quản lý phiên đăng nhập",
      description:
        "UC-14 — Xem và thu hồi từng phiên đăng nhập đang hoạt động trong hệ thống.",
      icon: MonitorSmartphone,
    },
    {
      to: "/data-sources",
      title: "Nguồn dữ liệu",
      description:
        "UC-015 — Đăng ký, xem, sửa và vô hiệu hoá nguồn dữ liệu (TABMIS, QLVBĐH, MISA, QL Giá, PMSTT).",
      icon: Database,
    },
    {
      to: "/connectors",
      title: "Thư viện bộ kết nối",
      description:
        "UC-016 — Xem danh sách, đăng ký (plugin) và cập nhật phiên bản bộ kết nối (tệp/REST API/JDBC/SOAP).",
      icon: Plug,
    },
    {
      to: "/source-connections",
      title: "Cấu hình kết nối nguồn",
      description:
        "UC-017 — Cấu hình connection (API/DB/File), kiểm thử kết nối, quản lý certificate/API key và cảnh báo hết hạn.",
      icon: PlugZap,
    },
    {
      to: "/datasets",
      title: "Định nghĩa tập dữ liệu của nguồn",
      description:
        "UC-018 — Định nghĩa lược đồ, khoá chính + phân mảnh, trường bắt buộc (NOT NULL), đăng ký Schema Registry.",
      icon: Layers,
    },
    {
      to: "/scheduled-tasks",
      title: "Cấu hình tác vụ điều phối",
      description:
        "UC-019 — Lịch cron, chế độ đồng bộ đầy đủ/tăng dần, chính sách thử lại; bật/tắt tác vụ.",
      icon: CalendarClock,
    },
    {
      to: "/ingestion-runs",
      title: "Lịch đầy đủ dữ liệu + Lịch sử chạy",
      description:
        "UC-020 — Xem lịch sử phiên ingest, heatmap kỳ thiếu dữ liệu, chi tiết log + tổng kiểm soát.",
      icon: History,
    },
    {
      to: "/incremental-sync",
      title: "Đồng bộ tăng dần từ API/DB",
      description:
        "UC-025 — Đọc điểm kiểm tra từ ingestion.runs, lấy dữ liệu mới/thay đổi (MISA/QL Giá/PMSTT), lưu MinIO + đẩy sự kiện parsing.requested.",
      icon: RefreshCw,
    },
    {
      to: "/schema-registry-checks",
      title: "Kiểm tra Schema Registry",
      description:
        "UC-026 — Trước khi phân tích, so sánh lược đồ nguồn với lược đồ đã đăng ký (UC-018); dừng xử lý + cảnh báo nếu phá vỡ tương thích, chuyển tiếp + ghi nhận nếu chỉ bổ sung.",
      icon: ShieldAlert,
    },
    {
      to: "/tabmis-intake",
      title: "Tiếp nhận file thủ công TABMIS",
      description:
        "UC-022 — Tải biểu mẫu Excel chuẩn, tải tệp lên: lưu raw vào MinIO, validate template + tổng kiểm soát, tạo phiên tiếp nhận + ghi ingestion.runs.",
      icon: UploadCloud,
    },
    {
      to: "/intake-reconciliation",
      title: "Đối soát phiên intake",
      description:
        "UC-027 — Chọn phiên tiếp nhận cần đối soát, xem tổng kiểm soát, đánh dấu phát hiện thiếu/sai, đóng phiên đối soát đạt yêu cầu để hệ thống cập nhật trạng thái.",
      icon: ClipboardCheck,
    },
    {
      to: "/reconciliation-tickets",
      title: "Xử lý ticket đối soát với chủ quản nguồn",
      description:
        "UC-028 — Mở ticket xử lý với chủ quản nguồn của phiên đối soát (lưu + thông báo), cập nhật tiến độ xử lý (lưu lịch sử), đóng ticket khi resolved (cập nhật trạng thái + ghi nhật ký).",
      icon: Ticket,
    },
    {
      to: "/qlvbdh-intake",
      title: "Tiếp nhận văn bản QLVBĐH",
      description:
        "UC-024 — Nhập siêu dữ liệu + đính kèm PDF/bản quét: lưu staging.stg_van_ban + MinIO (raw-documents), khử trùng lặp theo số ký hiệu, kích hoạt sự kiện ocr.requested.",
      icon: FileUp,
    },
    {
      to: "/ocr-jobs",
      title: "Phân tích PDF/bản quét + OCR",
      description:
        "UC-030 — Nhận sự kiện ocr.requested, chạy OCR PaddleOCR/olmOCR trên PDF/bản quét, trích xuất văn bản + bảng, lưu dữ liệu có cấu trúc, kích hoạt sự kiện ocr.completed + parsing.requested.",
      icon: FileScan,
    },
    {
      to: "/unmapped-queue",
      title: "Xử lý hàng đợi chưa ánh xạ",
      description:
        "UC-032 — Xem hàng đợi chưa ánh xạ (UC-031 đẩy vào), xử lý giá trị (ánh xạ/tạo mục mới/từ chối) để hệ thống lưu mapping mới, ánh xạ hàng loạt các giá trị tương tự để hệ thống áp dụng đồng loạt.",
      icon: Inbox,
    },
    {
      to: "/org-unit-catalog",
      title: "Quản lý danh mục đơn vị",
      description:
        "UC-033 — Xem danh mục đơn vị (cây phân cấp); thêm đơn vị mới (kiểm tra trùng mã, lưu phiên bản); sửa thông tin đơn vị; đóng/tách/sáp nhập đơn vị (lifecycle, lưu effective_from/effective_to).",
      icon: Network,
    },
    {
      to: "/budget-item-catalog",
      title: "Danh mục khoản mục NSNN",
      description:
        "UC-034 — Cây khoản mục NSNN (Chương/Loại/Khoản/Mục/Tiểu mục), quản lý phiên bản theo năm ngân sách, đề nghị thay đổi khoản mục nhạy cảm chờ duyệt.",
      icon: Landmark,
    },
    {
      to: "/asset-group-catalog",
      title: "Quản lý danh mục nhóm tài sản",
      description:
        "UC-035 — Xem danh mục nhóm tài sản (TT 45/2018 sửa TT 162/2014); thêm/sửa entry (hệ thống quản lý phiên bản); khai báo tỉ lệ khấu hao theo nhóm (hệ thống lưu).",
      icon: Percent,
    },
    {
      to: "/catalog-entries",
      title: "Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn",
      description:
        "UC-036 — Quản lý các danh mục dùng chung gồm mặt hàng, loại văn bản và nguồn vốn. Hỗ trợ xem danh sách, thêm, sửa, quản lý phiên bản và gửi yêu cầu thay đổi đối với các danh mục nhạy cảm để chờ phê duyệt.",
      icon: BookCopy,
    },
    {
      to: "/catalog-change-approvals",
      title: "Phê duyệt thay đổi danh mục nhạy cảm",
      description:
        "UC-037 — Xem các yêu cầu chờ duyệt, hệ thống hiển thị diff, phê duyệt/từ chối (áp dụng thay đổi vào danh mục + ghi lý do phê duyệt vào nhật ký).",
      icon: ClipboardCheck,
    },
    {
      to: "/quality-rules",
      title: "Quản lý quy tắc kiểm tra chất lượng",
      description:
        "UC-038 — Xem danh sách quy tắc chất lượng (đầy đủ/hợp lệ/duy nhất/nhất quán); thêm/sửa quy tắc (hệ thống lưu vào metadata.quality_rules + version); cấu hình ngưỡng + trọng số cho điểm (hệ thống lưu).",
      icon: Gauge,
    },
    {
      to: "/quality-checks",
      title: "Chạy kiểm tra chất lượng dữ liệu",
      description:
        "UC-039 — Nhận sự kiện mapping.completed: tra cứu quy tắc chất lượng + chạy từng quy tắc để tính điểm; đạt ngưỡng thì công bố vào kho chuẩn hoá, dưới ngưỡng thì đẩy vào hàng đợi ngoại lệ cho Phụ trách Dữ liệu.",
      icon: BadgeCheck,
    },
    {
      to: "/quality-exceptions",
      title: "Xử lý ngoại lệ chất lượng",
      description:
        "UC-040 — Xem hàng đợi ngoại lệ (UC-039 đẩy vào); xử lý từng ngoại lệ (sửa/từ chối/yêu cầu nguồn) để hệ thống lưu quyết định; xử lý hàng loạt ngoại lệ cùng loại để hệ thống áp dụng đồng loạt.",
      icon: ShieldAlert,
    },
    {
      to: "/curated-publish",
      title: "Công bố vào kho chuẩn hoá + batch_summary",
      description:
        "UC-041 — Nhận sự kiện curated.publish.requested (UC-039/UC-040): chèn/cập nhật dm_*, đặt publish_status=approved, tạo batch_summary + cập nhật độ mới dữ liệu, phát sự kiện curated.published.",
      icon: CloudUpload,
    },
    {
      to: "/dataset-metadata",
      title: "Đăng ký siêu dữ liệu tập dữ liệu",
      description:
        "UC-042 — Đăng ký siêu dữ liệu (chủ sở hữu/mô tả/mức nhạy cảm), hệ thống lưu vào metadata.dataset_catalog; cập nhật lưu phiên bản mới; tra cứu siêu dữ liệu, hệ thống hiển thị.",
      icon: Tag,
    },
    {
      to: "/semantic-indicators",
      title: "Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa",
      description:
        "UC-043 — Tạo chỉ tiêu mới (tên/mô tả/biểu thức/lĩnh vực), hệ thống lưu vào PostgreSQL; kiểm thử chỉ tiêu trên truy vấn mẫu, hệ thống chạy và hiển thị kết quả; quản lý phiên bản chỉ tiêu, hệ thống lưu version + audit.",
      icon: FlaskConical,
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
              <div
                style={{ fontSize: 13, color: "var(--color-text-secondary)" }}
              >
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
      <Route path="/auth/callback" element={<OidcCallbackPage />} />
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
      <Route
        path="/datasets"
        element={
          <ProtectedRoute>
            <DatasetsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scheduled-tasks"
        element={
          <ProtectedRoute>
            <ScheduledTasksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ingestion-runs"
        element={
          <ProtectedRoute>
            <IngestionRunsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/incremental-sync"
        element={
          <ProtectedRoute>
            <IncrementalSyncPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/schema-registry-checks"
        element={
          <ProtectedRoute>
            <SchemaRegistryChecksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/parsing-jobs"
        element={
          <ProtectedRoute>
            <ParsingJobsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/mapping-jobs"
        element={
          <ProtectedRoute>
            <MappingJobsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ocr-jobs"
        element={
          <ProtectedRoute>
            <OcrJobsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/unmapped-queue"
        element={
          <ProtectedRoute>
            <UnmappedQueuePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org-unit-catalog"
        element={
          <ProtectedRoute>
            <OrgUnitCatalogPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tabmis-intake"
        element={
          <ProtectedRoute>
            <TabmisIntakePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tabmis-intake/:id"
        element={
          <ProtectedRoute>
            <TabmisIntakeDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/intake-reconciliation"
        element={
          <ProtectedRoute>
            <IntakeReconciliationPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reconciliation-tickets"
        element={
          <ProtectedRoute>
            <ReconciliationTicketPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/budget-item-catalog"
        element={
          <ProtectedRoute>
            <BudgetItemCatalogPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/asset-group-catalog"
        element={
          <ProtectedRoute>
            <AssetGroupCatalogPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/catalog-entries"
        element={
          <ProtectedRoute>
            <CatalogEntriesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/catalog-change-approvals"
        element={
          <ProtectedRoute>
            <CatalogChangeApprovalsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quality-rules"
        element={
          <ProtectedRoute>
            <QualityRulesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quality-checks"
        element={
          <ProtectedRoute>
            <QualityChecksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quality-exceptions"
        element={
          <ProtectedRoute>
            <QualityExceptionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/qlvbdh-intake"
        element={
          <ProtectedRoute>
            <VanBanIntakePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/curated-publish"
        element={
          <ProtectedRoute>
            <CuratedPublishPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dataset-metadata"
        element={
          <ProtectedRoute>
            <DatasetMetadataPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/semantic-indicators"
        element={
          <ProtectedRoute>
            <SemanticIndicatorsPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}