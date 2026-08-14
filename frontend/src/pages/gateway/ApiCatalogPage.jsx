import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, History, RefreshCw } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  API_CATALOG_TYPES,
  configureApiCatalogVersion,
  listApiCatalog,
  listApiCatalogVersions,
  publishApiCatalogEntry,
  republishApiCatalogEntry,
  unpublishApiCatalogEntry,
} from "../../api/apiCatalog.js";

const API_TYPE_LABEL = {
  SEARCH: "Search — tra cứu ngữ nghĩa",
  QA: "QA — hỏi đáp có dẫn nguồn",
  DATA: "Data — dữ liệu ngân sách/tài sản/giá",
  METADATA: "Metadata — siêu dữ liệu/tài liệu liên quan",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_PUBLISH_FORM = {
  code: "",
  name: "",
  description: "",
  api_type: "SEARCH",
  endpoint_path: "",
  version: "v1",
  sunset_date: "",
};

const EMPTY_VERSION_FORM = {
  version: "",
  sunset_date: "",
  change_note: "",
};

export default function ApiCatalogPage() {
  const [entries, setEntries] = useState([]);
  const [apiTypeFilter, setApiTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [activeTab, setActiveTab] = useState("publish"); // publish | version

  const [publishForm, setPublishForm] = useState(EMPTY_PUBLISH_FORM);
  const [versionForm, setVersionForm] = useState(EMPTY_VERSION_FORM);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedEntry = entries.find((e) => e.id === selectedId) || null;

  async function loadEntries(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listApiCatalog({
        apiType: apiTypeFilter || null,
        status: statusFilter || null,
      });
      // Phòng trường hợp backend không tới được (proxy trả về HTML lỗi thay
      // vì JSON) — đảm bảo entries luôn là mảng để tránh crash toàn trang.
      const safeData = Array.isArray(data) ? data : [];
      setEntries(safeData);
      if (!keepSelection || !safeData.some((e) => e.id === selectedId)) {
        setSelectedId(safeData.length > 0 ? safeData[0].id : null);
      }
      if (!Array.isArray(data)) {
        setError("Không tải được danh mục API (phản hồi không hợp lệ từ máy chủ)");
      } else {
        setError(null);
      }
    } catch (err) {
      setEntries([]);
      setError(err?.response?.data?.detail?.message || "Không tải được danh mục API");
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(entryId) {
    if (!entryId) {
      setVersions([]);
      return;
    }
    try {
      const data = await listApiCatalogVersions(entryId);
      setVersions(Array.isArray(data) ? data : []);
    } catch {
      setVersions([]);
    }
  }

  useEffect(() => {
    loadEntries(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiTypeFilter, statusFilter]);

  useEffect(() => {
    loadVersions(selectedId);
    if (selectedEntry) {
      setVersionForm({
        version: selectedEntry.version,
        sunset_date: selectedEntry.sunset_date || "",
        change_note: "",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  // Bước 1 — Publish API mới -> hệ thống cập nhật danh mục.
  async function handlePublish(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    try {
      const payload = {
        ...publishForm,
        sunset_date: publishForm.sunset_date || null,
      };
      const created = await publishApiCatalogEntry(payload);
      setInfo(`Đã publish API "${created.name}" (${created.code}) vào danh mục.`);
      setPublishForm(EMPTY_PUBLISH_FORM);
      await loadEntries(false);
      setSelectedId(created.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Publish API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 2 — Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối.
  async function handleUnpublish(entryId) {
    clearMessages();
    setSubmitting(true);
    try {
      await unpublishApiCatalogEntry(entryId);
      setInfo("Đã gỡ công bố API — điểm cuối đã bị vô hiệu hoá.");
      await loadEntries(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Gỡ công bố API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRepublish(entryId) {
    clearMessages();
    setSubmitting(true);
    try {
      await republishApiCatalogEntry(entryId);
      setInfo("Đã công bố lại API.");
      await loadEntries(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Công bố lại API thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống lưu.
  async function handleConfigureVersion(e) {
    e.preventDefault();
    if (!selectedEntry) return;
    clearMessages();
    setSubmitting(true);
    try {
      const payload = {
        ...versionForm,
        sunset_date: versionForm.sunset_date || null,
      };
      await configureApiCatalogVersion(selectedEntry.id, payload);
      setInfo("Đã lưu cấu hình phiên bản + ngày ngừng hỗ trợ.");
      await loadEntries(true);
      await loadVersions(selectedEntry.id);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Cấu hình phiên bản thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Quản lý danh mục API"
      subtitle="UC-058 — Publish API mới (Search/QA/Data/Metadata); gỡ công bố API để vô hiệu hoá điểm cuối; cấu hình quản lý phiên bản + ngày ngừng hỗ trợ."
    >
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 12 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          <CheckCircle2 size={16} />
          <span>{info}</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        {/* ---------- Cột trái: danh mục API ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Danh mục API</h2>
            <button className="icon-btn" title="Tải lại" onClick={() => loadEntries(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="api-type-filter">Loại API</label>
                <select
                  id="api-type-filter"
                  value={apiTypeFilter}
                  onChange={(e) => setApiTypeFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  {API_CATALOG_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {API_TYPE_LABEL[t]}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="status-filter">Trạng thái</label>
                <select
                  id="status-filter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  <option value="PUBLISHED">Đang công bố</option>
                  <option value="UNPUBLISHED">Đã gỡ công bố</option>
                </select>
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : entries.length === 0 ? (
              <div className="empty-state">Chưa có API nào trong danh mục.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mã / Tên</th>
                    <th>Loại</th>
                    <th>Điểm cuối</th>
                    <th>Phiên bản</th>
                    <th>Ngừng hỗ trợ</th>
                    <th>Trạng thái</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr
                      key={entry.id}
                      onClick={() => setSelectedId(entry.id)}
                      style={{
                        cursor: "pointer",
                        background:
                          selectedId === entry.id ? "var(--color-primary-soft)" : undefined,
                      }}
                    >
                      <td>
                        <div>
                          <strong>{entry.name}</strong>
                        </div>
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {entry.code}
                        </div>
                      </td>
                      <td style={{ fontSize: 13 }}>{entry.api_type}</td>
                      <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                        {entry.endpoint_path}
                      </td>
                      <td>{entry.version}</td>
                      <td style={{ fontSize: 13 }}>{entry.sunset_date || "—"}</td>
                      <td>
                        <span
                          className={`badge ${
                            entry.status === "PUBLISHED" ? "badge-success" : "badge-neutral"
                          }`}
                        >
                          {entry.status === "PUBLISHED" ? "Đang công bố" : "Đã gỡ công bố"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          {entry.status === "PUBLISHED" ? (
                            <button
                              className="btn btn-danger-ghost"
                              disabled={submitting}
                              onClick={(ev) => {
                                ev.stopPropagation();
                                handleUnpublish(entry.id);
                              }}
                            >
                              Gỡ công bố
                            </button>
                          ) : (
                            <button
                              className="btn btn-secondary"
                              disabled={submitting}
                              onClick={(ev) => {
                                ev.stopPropagation();
                                handleRepublish(entry.id);
                              }}
                            >
                              Công bố lại
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Cột phải: thao tác ---------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2>
                {activeTab === "publish"
                  ? "Publish API mới"
                  : `Cấu hình phiên bản${selectedEntry ? ` — ${selectedEntry.code}` : ""}`}
              </h2>
            </div>
            <div className="card-body">
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <button
                  className={`btn ${activeTab === "publish" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActiveTab("publish")}
                >
                  Publish API mới
                </button>
                <button
                  className={`btn ${activeTab === "version" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setActiveTab("version")}
                  disabled={!selectedEntry}
                >
                  Cấu hình phiên bản
                </button>
              </div>

              {activeTab === "publish" && (
                <form onSubmit={handlePublish} className="form-grid">
                  <div className="field">
                    <label htmlFor="p-code">Mã API *</label>
                    <input
                      id="p-code"
                      required
                      value={publishForm.code}
                      onChange={(e) => setPublishForm({ ...publishForm, code: e.target.value })}
                      placeholder="vd: API-SEARCH-DOCS"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="p-name">Tên API *</label>
                    <input
                      id="p-name"
                      required
                      value={publishForm.name}
                      onChange={(e) => setPublishForm({ ...publishForm, name: e.target.value })}
                    />
                  </div>
                  <div className="field field-full">
                    <label htmlFor="p-description">Mô tả</label>
                    <textarea
                      id="p-description"
                      rows={2}
                      value={publishForm.description}
                      onChange={(e) =>
                        setPublishForm({ ...publishForm, description: e.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="p-type">Loại API</label>
                    <select
                      id="p-type"
                      value={publishForm.api_type}
                      onChange={(e) =>
                        setPublishForm({ ...publishForm, api_type: e.target.value })
                      }
                    >
                      {API_CATALOG_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="p-version">Phiên bản *</label>
                    <input
                      id="p-version"
                      required
                      value={publishForm.version}
                      onChange={(e) =>
                        setPublishForm({ ...publishForm, version: e.target.value })
                      }
                    />
                  </div>
                  <div className="field field-full">
                    <label htmlFor="p-endpoint">Đường dẫn điểm cuối *</label>
                    <input
                      id="p-endpoint"
                      required
                      value={publishForm.endpoint_path}
                      onChange={(e) =>
                        setPublishForm({ ...publishForm, endpoint_path: e.target.value })
                      }
                      style={{ fontFamily: "monospace" }}
                      placeholder="/v1/search/documents"
                    />
                  </div>
                  <div className="field field-full">
                    <label htmlFor="p-sunset">Ngày ngừng hỗ trợ (tuỳ chọn)</label>
                    <input
                      id="p-sunset"
                      type="date"
                      value={publishForm.sunset_date}
                      onChange={(e) =>
                        setPublishForm({ ...publishForm, sunset_date: e.target.value })
                      }
                    />
                  </div>
                  <div className="field field-full">
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      {submitting ? "Đang xử lý..." : "Publish API"}
                    </button>
                  </div>
                </form>
              )}

              {activeTab === "version" && selectedEntry && (
                <form onSubmit={handleConfigureVersion} className="form-grid">
                  <div className="field field-full">
                    <small>
                      API: <strong>{selectedEntry.name}</strong> ({selectedEntry.code})
                    </small>
                  </div>
                  <div className="field">
                    <label htmlFor="v-version">Phiên bản mới *</label>
                    <input
                      id="v-version"
                      required
                      value={versionForm.version}
                      onChange={(e) =>
                        setVersionForm({ ...versionForm, version: e.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="v-sunset">Ngày ngừng hỗ trợ</label>
                    <input
                      id="v-sunset"
                      type="date"
                      value={versionForm.sunset_date}
                      onChange={(e) =>
                        setVersionForm({ ...versionForm, sunset_date: e.target.value })
                      }
                    />
                  </div>
                  <div className="field field-full">
                    <label htmlFor="v-note">Ghi chú thay đổi</label>
                    <input
                      id="v-note"
                      value={versionForm.change_note}
                      onChange={(e) =>
                        setVersionForm({ ...versionForm, change_note: e.target.value })
                      }
                    />
                  </div>
                  <div className="field field-full">
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      {submitting ? "Đang xử lý..." : "Lưu cấu hình phiên bản"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {selectedEntry && (
            <div className="card">
              <div className="card-header">
                <h2>
                  <History size={15} style={{ verticalAlign: "middle", marginRight: 6 }} />
                  Lịch sử phiên bản
                </h2>
              </div>
              <div className="card-body">
                {versions.length === 0 ? (
                  <div className="empty-state">Chưa có lịch sử.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {versions.map((v) => (
                      <div
                        key={v.id}
                        style={{
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-sm)",
                          padding: 10,
                        }}
                      >
                        <div style={{ fontSize: 13 }}>
                          <strong>v{v.version_no}</strong> — {v.version}
                          {v.sunset_date ? ` (ngừng hỗ trợ: ${v.sunset_date})` : ""}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          {v.change_note} · {formatTime(v.created_at)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}