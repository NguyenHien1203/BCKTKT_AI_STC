import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, History, RefreshCw, ShieldCheck } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  SENSITIVITY_LEVELS,
  getDatasetMetadata,
  listDatasetMetadata,
  listDatasetMetadataVersions,
  registerDatasetMetadata,
  updateDatasetMetadata,
} from "../../api/datasetMetadata.js";
import { listDatasets } from "../../api/datasets.js";

const SENSITIVITY_LABEL = {
  PUBLIC: "Công khai",
  INTERNAL: "Nội bộ",
  CONFIDENTIAL: "Bí mật",
  SECRET: "Tuyệt mật",
};

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const EMPTY_REGISTER_FORM = {
  dataset_id: "",
  owner: "",
  description: "",
  sensitivity_level: "INTERNAL",
  note: "",
};
const EMPTY_UPDATE_FORM = {
  owner: "",
  description: "",
  sensitivity_level: "INTERNAL",
  note: "",
};

export default function DatasetMetadataPage() {
  const [items, setItems] = useState([]);
  const [sensitivityFilter, setSensitivityFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [datasets, setDatasets] = useState([]);

  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedMetadata, setSelectedMetadata] = useState(null);
  const [versions, setVersions] = useState([]);
  const [activeTab, setActiveTab] = useState("register"); // register | update

  const [registerForm, setRegisterForm] = useState(EMPTY_REGISTER_FORM);
  const [updateForm, setUpdateForm] = useState(EMPTY_UPDATE_FORM);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function loadItems() {
    setLoading(true);
    try {
      const data = await listDatasetMetadata({
        sensitivityLevel: sensitivityFilter || null,
        owner: ownerFilter || null,
      });
      setItems(data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDatasets() {
    try {
      const data = await listDatasets();
      setDatasets(data);
    } catch {
      // Danh sách tập dữ liệu (UC-018) chỉ để tiện chọn nhanh -- không
      // chặn UC-042 nếu ingestion-service tạm thời không truy cập được;
      // vẫn có thể nhập trực tiếp dataset_id.
      setDatasets([]);
    }
  }

  async function loadDetail(datasetId) {
    if (!datasetId) {
      setSelectedMetadata(null);
      setVersions([]);
      return;
    }
    try {
      const metadata = await getDatasetMetadata(datasetId);
      setSelectedMetadata(metadata);
      const v = await listDatasetMetadataVersions(datasetId);
      setVersions(v);
      setUpdateForm({
        owner: metadata.owner,
        description: metadata.description || "",
        sensitivity_level: metadata.sensitivity_level,
        note: "",
      });
      setActiveTab("update");
    } catch (e) {
      setSelectedMetadata(null);
      setVersions([]);
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadItems();
    loadDatasets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sensitivityFilter, ownerFilter]);

  async function handleRegister(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await registerDatasetMetadata({
        datasetId: Number(registerForm.dataset_id),
        owner: registerForm.owner.trim(),
        description: registerForm.description.trim() || null,
        sensitivityLevel: registerForm.sensitivity_level,
        note: registerForm.note.trim() || null,
      });
      setInfo(
        `Đã đăng ký siêu dữ liệu cho tập dữ liệu id=${created.dataset_id} (phiên bản ${created.version}).`,
      );
      setError(null);
      setRegisterForm(EMPTY_REGISTER_FORM);
      await loadItems();
      setSelectedDatasetId(created.dataset_id);
      await loadDetail(created.dataset_id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!selectedMetadata) return;
    setSubmitting(true);
    try {
      const clearDescription =
        !!selectedMetadata.description && updateForm.description.trim() === "";
      const updated = await updateDatasetMetadata(selectedMetadata.dataset_id, {
        owner: updateForm.owner.trim() || null,
        description: updateForm.description.trim() || null,
        clearDescription,
        sensitivityLevel: updateForm.sensitivity_level || null,
        note: updateForm.note.trim() || null,
      });
      setInfo(
        `Đã cập nhật siêu dữ liệu tập dữ liệu id=${updated.dataset_id} -- phiên bản mới: ${updated.version}.`,
      );
      setError(null);
      setUpdateForm((f) => ({ ...f, note: "" }));
      await loadItems();
      await loadDetail(updated.dataset_id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Đăng ký siêu dữ liệu tập dữ liệu"
      subtitle="UC-042 — Đăng ký siêu dữ liệu (chủ sở hữu, mô tả, mức nhạy cảm), hệ thống lưu vào metadata.dataset_catalog; cập nhật siêu dữ liệu, hệ thống lưu phiên bản mới; tra cứu siêu dữ liệu, hệ thống hiển thị."
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

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 20 }}>
        {/* ---------- Bước 3: Tra cứu (danh sách) ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>Bước 3 — Tra cứu siêu dữ liệu tập dữ liệu</h2>
            <button className="icon-btn" title="Làm mới" onClick={loadItems}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid" style={{ marginBottom: 12 }}>
              <div className="field">
                <label htmlFor="sensitivity-filter">Mức nhạy cảm</label>
                <select
                  id="sensitivity-filter"
                  value={sensitivityFilter}
                  onChange={(e) => setSensitivityFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  {SENSITIVITY_LEVELS.map((s) => (
                    <option key={s} value={s}>
                      {SENSITIVITY_LABEL[s]}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="owner-filter">Chủ sở hữu</label>
                <input
                  id="owner-filter"
                  value={ownerFilter}
                  onChange={(e) => setOwnerFilter(e.target.value)}
                  placeholder="Lọc theo chủ sở hữu..."
                />
              </div>
            </div>

            {loading ? (
              <p>Đang tải...</p>
            ) : items.length === 0 ? (
              <p style={{ color: "var(--color-text-secondary, #888)" }}>
                Chưa có tập dữ liệu nào được đăng ký siêu dữ liệu.
              </p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Dataset id</th>
                    <th>Chủ sở hữu</th>
                    <th>Mức nhạy cảm</th>
                    <th>Phiên bản</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((m) => (
                    <tr
                      key={m.id}
                      onClick={() => {
                        setSelectedDatasetId(m.dataset_id);
                        loadDetail(m.dataset_id);
                      }}
                      style={{
                        cursor: "pointer",
                        background:
                          selectedDatasetId === m.dataset_id
                            ? "var(--color-bg-hover, #f5f7fa)"
                            : undefined,
                      }}
                    >
                      <td>
                        <strong>{m.dataset_id}</strong>
                      </td>
                      <td>{m.owner}</td>
                      <td>
                        <span className="badge">{SENSITIVITY_LABEL[m.sensitivity_level]}</span>
                      </td>
                      <td>v{m.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ---------- Bước 1 & 2: Thao tác ---------- */}
        <div className="card">
          <div className="card-header">
            <h2>
              {selectedMetadata
                ? `Siêu dữ liệu tập dữ liệu id=${selectedMetadata.dataset_id}`
                : "Đăng ký siêu dữ liệu mới"}
            </h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button
                className={`btn ${activeTab === "register" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab("register")}
              >
                Đăng ký mới
              </button>
              <button
                className={`btn ${activeTab === "update" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab("update")}
                disabled={!selectedMetadata}
              >
                Cập nhật
              </button>
            </div>

            {activeTab === "register" && (
              <form onSubmit={handleRegister} className="form-grid">
                <div className="field">
                  <label htmlFor="r-dataset">Tập dữ liệu (dataset_id) *</label>
                  {datasets.length > 0 ? (
                    <select
                      id="r-dataset"
                      required
                      value={registerForm.dataset_id}
                      onChange={(e) =>
                        setRegisterForm((f) => ({ ...f, dataset_id: e.target.value }))
                      }
                    >
                      <option value="">-- Chọn tập dữ liệu --</option>
                      {datasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.code} — {d.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id="r-dataset"
                      type="number"
                      required
                      value={registerForm.dataset_id}
                      onChange={(e) =>
                        setRegisterForm((f) => ({ ...f, dataset_id: e.target.value }))
                      }
                      placeholder="Nhập id tập dữ liệu (UC-018)"
                    />
                  )}
                </div>
                <div className="field">
                  <label htmlFor="r-owner">Chủ sở hữu *</label>
                  <input
                    id="r-owner"
                    required
                    value={registerForm.owner}
                    onChange={(e) => setRegisterForm((f) => ({ ...f, owner: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-sensitivity">Mức nhạy cảm *</label>
                  <select
                    id="r-sensitivity"
                    value={registerForm.sensitivity_level}
                    onChange={(e) =>
                      setRegisterForm((f) => ({ ...f, sensitivity_level: e.target.value }))
                    }
                  >
                    {SENSITIVITY_LEVELS.map((s) => (
                      <option key={s} value={s}>
                        {SENSITIVITY_LABEL[s]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field field-full">
                  <label htmlFor="r-description">Mô tả</label>
                  <textarea
                    id="r-description"
                    rows={3}
                    value={registerForm.description}
                    onChange={(e) =>
                      setRegisterForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="r-note">Ghi chú</label>
                  <input
                    id="r-note"
                    value={registerForm.note}
                    onChange={(e) => setRegisterForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    <ShieldCheck size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    {submitting ? "Đang lưu..." : "Đăng ký siêu dữ liệu"}
                  </button>
                </div>
              </form>
            )}

            {activeTab === "update" && selectedMetadata && (
              <form onSubmit={handleUpdate} className="form-grid">
                <div className="field">
                  <label htmlFor="u-owner">Chủ sở hữu</label>
                  <input
                    id="u-owner"
                    value={updateForm.owner}
                    onChange={(e) => setUpdateForm((f) => ({ ...f, owner: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="u-sensitivity">Mức nhạy cảm</label>
                  <select
                    id="u-sensitivity"
                    value={updateForm.sensitivity_level}
                    onChange={(e) =>
                      setUpdateForm((f) => ({ ...f, sensitivity_level: e.target.value }))
                    }
                  >
                    {SENSITIVITY_LEVELS.map((s) => (
                      <option key={s} value={s}>
                        {SENSITIVITY_LABEL[s]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field field-full">
                  <label htmlFor="u-description">Mô tả (để trống để xoá)</label>
                  <textarea
                    id="u-description"
                    rows={3}
                    value={updateForm.description}
                    onChange={(e) =>
                      setUpdateForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
                <div className="field field-full">
                  <label htmlFor="u-note">Ghi chú thay đổi</label>
                  <input
                    id="u-note"
                    value={updateForm.note}
                    onChange={(e) => setUpdateForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>
                <div className="field field-full">
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting
                      ? "Đang lưu..."
                      : `Lưu (tạo phiên bản v${selectedMetadata.version + 1})`}
                  </button>
                </div>
              </form>
            )}

            {selectedMetadata && (
              <>
                <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                  <History size={16} /> Lịch sử phiên bản
                </h3>
                {versions.length === 0 ? (
                  <p style={{ color: "var(--color-text-secondary, #888)" }}>Chưa có lịch sử.</p>
                ) : (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Phiên bản</th>
                        <th>Chủ sở hữu</th>
                        <th>Mức nhạy cảm</th>
                        <th>Ghi chú</th>
                        <th>Thời điểm</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id}>
                          <td>v{v.version}</td>
                          <td>{v.owner}</td>
                          <td>{SENSITIVITY_LABEL[v.sensitivity_level]}</td>
                          <td>{v.change_note || "—"}</td>
                          <td>{formatTime(v.changed_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}