import { useEffect, useState } from "react";
import { AlertCircle, BookOpen, ExternalLink, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  API_DOCS_REDOC_URL,
  API_DOCS_SWAGGER_URL,
  getPublishedApiDocsCatalog,
} from "../../api/apiDocs.js";

const API_TYPE_LABEL = {
  SEARCH: "Search — tra cứu ngữ nghĩa",
  QA: "QA — hỏi đáp có dẫn nguồn",
  DATA: "Data — dữ liệu ngân sách/tài sản/giá",
  METADATA: "Metadata — siêu dữ liệu/tài liệu liên quan",
};

export default function ApiDocsPage() {
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeViewer, setActiveViewer] = useState("swagger"); // swagger | redoc

  async function loadCatalog() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublishedApiDocsCatalog();
      setEntries(data);
    } catch (err) {
      setError(
        err?.response?.data?.detail?.message ||
          "Không tải được danh mục API đang công bố"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const viewerUrl = activeViewer === "swagger" ? API_DOCS_SWAGGER_URL : API_DOCS_REDOC_URL;

  return (
    <AppLayout
      title="Cổng tài liệu API"
      subtitle="UC-063 — Đơn vị khai thác (QLVBĐH, IOC, LGSP) truy cập cổng Swagger/Redoc; hệ thống hiển thị UI để xem tài liệu các API đã công bố."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>Danh mục API đang công bố</h2>
          <button className="icon-btn" title="Tải lại" onClick={loadCatalog}>
            <RefreshCw size={15} />
          </button>
        </div>
        <div className="card-body">
          {loading ? (
            <p>Đang tải…</p>
          ) : entries.length === 0 ? (
            <p style={{ color: "var(--muted, #666)" }}>
              Chưa có API nào đang công bố. Xem mục "Quản lý danh mục API" (UC-058) để publish API mới.
            </p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Tên</th>
                  <th>Loại</th>
                  <th>Điểm cuối</th>
                  <th>Phiên bản</th>
                  <th>Ngày ngừng hỗ trợ</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.code}</td>
                    <td>{entry.name}</td>
                    <td>{API_TYPE_LABEL[entry.api_type] || entry.api_type}</td>
                    <td>
                      <code>{entry.endpoint_path}</code>
                    </td>
                    <td>{entry.version}</td>
                    <td>{entry.sunset_date || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>
            <BookOpen size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Xem tài liệu API
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className={activeViewer === "swagger" ? "btn btn-primary" : "btn"}
              onClick={() => setActiveViewer("swagger")}
            >
              Swagger UI
            </button>
            <button
              className={activeViewer === "redoc" ? "btn btn-primary" : "btn"}
              onClick={() => setActiveViewer("redoc")}
            >
              ReDoc
            </button>
            <a
              className="btn"
              href={viewerUrl}
              target="_blank"
              rel="noreferrer"
              title="Mở ở tab mới"
            >
              <ExternalLink size={14} style={{ verticalAlign: "-2px", marginRight: 4 }} />
              Mở tab mới
            </a>
          </div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {/* Hệ thống hiển thị UI Swagger/Redoc ngay trong cổng tài liệu — đơn vị
              khai thác có thể xem trực tiếp mà không cần rời khỏi trang. */}
          <iframe
            key={activeViewer}
            title={`Cổng tài liệu API — ${activeViewer === "swagger" ? "Swagger UI" : "ReDoc"}`}
            src={viewerUrl}
            style={{ width: "100%", height: 640, border: "none" }}
          />
        </div>
      </div>
    </AppLayout>
  );
}