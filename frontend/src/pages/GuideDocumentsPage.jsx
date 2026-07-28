import { useEffect, useState } from "react";
import {
  AlertCircle,
  Download,
  FileText,
  History,
  Plus,
  RotateCcw,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import {
  addGuideDocument,
  deleteGuideDocument,
  downloadGuideDocument,
  listGuideDocumentVersions,
  listGuideDocuments,
  restoreGuideDocument,
  updateGuideDocument,
} from "../api/guideDocuments.js";

const EMPTY_FORM = { title: "", description: "", category: "", uploadedBy: "admin" };

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function formatSize(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`;
}

export default function GuideDocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [onlyActive, setOnlyActive] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState(EMPTY_FORM);
  const [addFile, setAddFile] = useState(null);
  const [saving, setSaving] = useState(false);

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editFile, setEditFile] = useState(null);

  const [versionsFor, setVersionsFor] = useState(null);
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  async function reload(activeOnly = onlyActive) {
    setLoading(true);
    try {
      const data = await listGuideDocuments({ onlyActive: activeOnly });
      setDocuments(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload(onlyActive);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyActive]);

  function flashSuccess(message) {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 3000);
  }

  async function handleAddSubmit(e) {
    e.preventDefault();
    if (!addFile) {
      setError("Vui lòng chọn tệp tài liệu");
      return;
    }
    setSaving(true);
    try {
      await addGuideDocument({ ...addForm, file: addFile });
      setAddForm(EMPTY_FORM);
      setAddFile(null);
      setShowAddForm(false);
      flashSuccess("Đã thêm tài liệu mới");
      await reload();
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSaving(false);
    }
  }

  function startEdit(doc) {
    setEditingId(doc.id);
    setEditForm({
      title: doc.title,
      description: doc.description,
      category: doc.category,
      uploadedBy: "admin",
    });
    setEditFile(null);
  }

  async function handleEditSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await updateGuideDocument(editingId, { ...editForm, file: editFile });
      setEditingId(null);
      setEditFile(null);
      flashSuccess(editFile ? "Đã lưu tài liệu — phiên bản mới đã được tạo" : "Đã lưu thay đổi");
      await reload();
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(doc) {
    if (!window.confirm(`Xoá tài liệu "${doc.title}"? (xoá mềm, có thể khôi phục lại)`)) return;
    try {
      await deleteGuideDocument(doc.id);
      flashSuccess("Đã xoá tài liệu");
      await reload();
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleRestore(doc) {
    try {
      await restoreGuideDocument(doc.id);
      flashSuccess("Đã khôi phục tài liệu");
      await reload();
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  async function handleShowVersions(doc) {
    setVersionsFor(doc);
    setVersionsLoading(true);
    try {
      const data = await listGuideDocumentVersions(doc.id);
      setVersions(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setVersionsLoading(false);
    }
  }

  async function handleDownload(doc, version) {
    try {
      const { blob } = await downloadGuideDocument(doc.id, version);
      const fileName =
        version && versions.find((v) => v.version === version)
          ? versions.find((v) => v.version === version).file_name
          : doc.file_name;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  return (
    <AppLayout
      title="Quản trị tài liệu hướng dẫn sử dụng"
      subtitle="UC-11 — Thêm/sửa/xoá tài liệu hướng dẫn (lưu tệp vào MinIO, quản lý phiên bản khi sửa, xoá mềm)."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <span>{success}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div
          className="card-header"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <h2>
            <FileText size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Thêm tài liệu mới
          </h2>
          <button className="btn btn-primary" onClick={() => setShowAddForm((v) => !v)}>
            <Plus size={15} />
            {showAddForm ? "Đóng" : "Thêm tài liệu"}
          </button>
        </div>
        {showAddForm && (
          <div className="card-body">
            <form onSubmit={handleAddSubmit}>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="add-title">Tiêu đề *</label>
                  <input
                    id="add-title"
                    required
                    value={addForm.title}
                    onChange={(e) => setAddForm({ ...addForm, title: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="add-category">Danh mục</label>
                  <input
                    id="add-category"
                    placeholder="vd: BAO_CAO, AI, NGAN_SACH..."
                    value={addForm.category}
                    onChange={(e) => setAddForm({ ...addForm, category: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="add-uploaded-by">Người tạo</label>
                  <input
                    id="add-uploaded-by"
                    value={addForm.uploadedBy}
                    onChange={(e) => setAddForm({ ...addForm, uploadedBy: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="add-file">Tệp tài liệu *</label>
                  <input
                    id="add-file"
                    type="file"
                    required
                    onChange={(e) => setAddFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
              <div className="field" style={{ marginTop: 12 }}>
                <label htmlFor="add-description">Mô tả</label>
                <textarea
                  id="add-description"
                  rows={2}
                  value={addForm.description}
                  onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                />
              </div>
              <div style={{ marginTop: 12 }}>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  <Upload size={15} />
                  {saving ? "Đang lưu..." : "Lưu tài liệu"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {versionsFor && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div
            className="card-header"
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
          >
            <h2>
              <History size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
              Lịch sử phiên bản — {versionsFor.title}
            </h2>
            <button className="icon-btn" title="Đóng" onClick={() => setVersionsFor(null)}>
              <X size={15} />
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {versionsLoading ? (
              <div className="empty-state">Đang tải...</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Phiên bản</th>
                    <th>Tên tệp</th>
                    <th>Dung lượng</th>
                    <th>Người tải lên</th>
                    <th>Thời gian</th>
                    <th>Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((v) => (
                    <tr key={v.id}>
                      <td>v{v.version}</td>
                      <td>{v.file_name}</td>
                      <td>{formatSize(v.file_size)}</td>
                      <td>{v.uploaded_by || "—"}</td>
                      <td>{formatTime(v.created_at)}</td>
                      <td>
                        <button
                          className="icon-btn"
                          title="Tải phiên bản này"
                          onClick={() => handleDownload(versionsFor, v.version)}
                        >
                          <Download size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <div
          className="card-header"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <h2>
            <FileText size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Danh sách tài liệu ({documents.length})
          </h2>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={onlyActive}
              onChange={(e) => setOnlyActive(e.target.checked)}
            />
            Chỉ hiển thị tài liệu đang hoạt động
          </label>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Đang tải dữ liệu...</div>
          ) : documents.length === 0 ? (
            <div className="empty-state">Chưa có tài liệu hướng dẫn nào.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tiêu đề</th>
                  <th>Danh mục</th>
                  <th>Tệp</th>
                  <th>Phiên bản</th>
                  <th>Trạng thái</th>
                  <th>Cập nhật</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <>
                    <tr key={doc.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{doc.title}</div>
                        {doc.description && (
                          <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                            {doc.description}
                          </div>
                        )}
                      </td>
                      <td>{doc.category || "—"}</td>
                      <td>
                        {doc.file_name} ({formatSize(doc.file_size)})
                      </td>
                      <td>v{doc.current_version}</td>
                      <td>
                        {doc.is_active ? (
                          <span className="badge badge-success">Đang hoạt động</span>
                        ) : (
                          <span className="badge badge-neutral">Đã xoá</span>
                        )}
                      </td>
                      <td>{formatTime(doc.updated_at)}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-btn"
                            title="Tải tệp hiện tại"
                            onClick={() => handleDownload(doc)}
                          >
                            <Download size={15} />
                          </button>
                          <button
                            className="icon-btn"
                            title="Xem lịch sử phiên bản"
                            onClick={() => handleShowVersions(doc)}
                          >
                            <History size={15} />
                          </button>
                          <button className="icon-btn" title="Sửa tài liệu" onClick={() => startEdit(doc)}>
                            <FileText size={15} />
                          </button>
                          {doc.is_active ? (
                            <button
                              className="icon-btn"
                              title="Xoá tài liệu (xoá mềm)"
                              onClick={() => handleDelete(doc)}
                            >
                              <Trash2 size={15} />
                            </button>
                          ) : (
                            <button
                              className="icon-btn"
                              title="Khôi phục tài liệu"
                              onClick={() => handleRestore(doc)}
                            >
                              <RotateCcw size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {editingId === doc.id && (
                      <tr>
                        <td colSpan={7} style={{ background: "var(--color-surface-alt)" }}>
                          <form onSubmit={handleEditSubmit} style={{ padding: 12 }}>
                            <div className="form-grid">
                              <div className="field">
                                <label>Tiêu đề</label>
                                <input
                                  value={editForm.title}
                                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                                />
                              </div>
                              <div className="field">
                                <label>Danh mục</label>
                                <input
                                  value={editForm.category}
                                  onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                                />
                              </div>
                              <div className="field">
                                <label>Người sửa</label>
                                <input
                                  value={editForm.uploadedBy}
                                  onChange={(e) => setEditForm({ ...editForm, uploadedBy: e.target.value })}
                                />
                              </div>
                              <div className="field">
                                <label>Thay tệp mới (tuỳ chọn — sẽ tăng phiên bản)</label>
                                <input
                                  type="file"
                                  onChange={(e) => setEditFile(e.target.files?.[0] || null)}
                                />
                              </div>
                            </div>
                            <div className="field" style={{ marginTop: 8 }}>
                              <label>Mô tả</label>
                              <textarea
                                rows={2}
                                value={editForm.description}
                                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                              />
                            </div>
                            <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                              <button type="submit" className="btn btn-primary" disabled={saving}>
                                {saving ? "Đang lưu..." : "Lưu thay đổi"}
                              </button>
                              <button
                                type="button"
                                className="btn"
                                onClick={() => setEditingId(null)}
                              >
                                Huỷ
                              </button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  );
}