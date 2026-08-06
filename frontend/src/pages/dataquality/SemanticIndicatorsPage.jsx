import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, FlaskConical, History, RefreshCw, ScrollText } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  INDICATOR_STATUSES,
  createSemanticIndicator,
  listIndicatorTestRuns,
  listSemanticIndicatorAuditLogs,
  listSemanticIndicatorVersions,
  listSemanticIndicators,
  testSemanticIndicator,
  updateSemanticIndicator,
} from "../../api/semanticIndicators.js";

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

function statusLabel(status) {
  return INDICATOR_STATUSES.find((s) => s.value === status)?.label || status;
}

function statusBadgeClass(status) {
  if (status === "ACTIVE") return "badge badge-success";
  if (status === "INACTIVE") return "badge badge-danger";
  return "badge badge-neutral";
}

function testStatusBadgeClass(status) {
  return status === "SUCCESS" ? "badge badge-success" : "badge badge-danger";
}

const TWO_COL_GRID = { display: "grid", gridTemplateColumns: "minmax(320px, 1fr) minmax(380px, 1.3fr)", gap: 20 };
const TWO_COL_GRID_EVEN = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 };

const EMPTY_CREATE_FORM = {
  name: "",
  domain: "",
  expression: "",
  description: "",
  created_by: "",
  note: "",
};
const EMPTY_EDIT_FORM = {
  name: "",
  domain: "",
  expression: "",
  description: "",
  status: "DRAFT",
  changed_by: "",
  note: "",
};
const SAMPLE_ROWS_PLACEHOLDER = `[
  { "so_tien": 1000000 },
  { "so_tien": 2500000 }
]`;

export default function SemanticIndicatorsPage() {
  const [domainFilter, setDomainFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [indicators, setIndicators] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [testRuns, setTestRuns] = useState([]);
  const [activePanel, setActivePanel] = useState("create"); // create | edit

  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM);

  const [sampleRowsText, setSampleRowsText] = useState(SAMPLE_ROWS_PLACEHOLDER);
  const [testedBy, setTestedBy] = useState("");
  const [lastTestRun, setLastTestRun] = useState(null);
  const [testError, setTestError] = useState(null);
  const [testSubmitting, setTestSubmitting] = useState(false);

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedIndicator = indicators.find((i) => i.id === selectedId) || null;

  async function loadIndicators(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listSemanticIndicators({
        domain: domainFilter.trim() || null,
        status: statusFilter || null,
      });
      setIndicators(data);
      if (!keepSelection || !data.some((i) => i.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetails(indicatorId) {
    if (!indicatorId) {
      setVersions([]);
      setAuditLogs([]);
      setTestRuns([]);
      return;
    }
    try {
      const [v, a, t] = await Promise.all([
        listSemanticIndicatorVersions(indicatorId),
        listSemanticIndicatorAuditLogs(indicatorId),
        listIndicatorTestRuns(indicatorId),
      ]);
      setVersions(v);
      setAuditLogs(a);
      setTestRuns(t);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    }
  }

  useEffect(() => {
    loadIndicators(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainFilter, statusFilter]);

  useEffect(() => {
    loadDetails(selectedId);
    setLastTestRun(null);
    setTestError(null);
    if (selectedIndicator) {
      setEditForm({
        name: selectedIndicator.name,
        domain: selectedIndicator.domain,
        expression: selectedIndicator.expression,
        description: selectedIndicator.description || "",
        status: selectedIndicator.status,
        changed_by: "",
        note: "",
      });
      setActivePanel("edit");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await createSemanticIndicator({
        name: createForm.name.trim(),
        expression: createForm.expression.trim(),
        domain: createForm.domain.trim(),
        description: createForm.description.trim() || null,
        createdBy: createForm.created_by.trim() || null,
        note: createForm.note.trim() || null,
      });
      setInfo(`Đã tạo chỉ tiêu "${created.name}" (phiên bản ${created.version}, trạng thái ${statusLabel(created.status)}).`);
      setError(null);
      setCreateForm(EMPTY_CREATE_FORM);
      await loadIndicators(false);
      setSelectedId(created.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!selectedIndicator) return;
    setSubmitting(true);
    try {
      const clearDescription = editForm.description.trim() === "" && !!selectedIndicator.description;
      const updated = await updateSemanticIndicator(selectedIndicator.id, {
        name: editForm.name.trim() || null,
        description: editForm.description.trim() || null,
        clearDescription,
        expression: editForm.expression.trim() || null,
        domain: editForm.domain.trim() || null,
        status: editForm.status || null,
        changedBy: editForm.changed_by.trim() || null,
        note: editForm.note.trim() || null,
      });
      setInfo(`Đã lưu chỉ tiêu — phiên bản mới: ${updated.version} (${statusLabel(updated.status)}).`);
      setError(null);
      setEditForm((f) => ({ ...f, note: "" }));
      await loadIndicators(true);
      await loadDetails(selectedIndicator.id);
    } catch (e2) {
      setError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRunTest(e) {
    e.preventDefault();
    if (!selectedIndicator) return;
    setTestError(null);
    let sampleRows;
    try {
      sampleRows = JSON.parse(sampleRowsText);
      if (!Array.isArray(sampleRows) || sampleRows.length === 0) {
        throw new Error("Tập bản ghi mẫu phải là 1 mảng JSON, ít nhất 1 bản ghi.");
      }
    } catch (parseErr) {
      setTestError(`Tập bản ghi mẫu không hợp lệ (JSON): ${parseErr.message}`);
      return;
    }
    setTestSubmitting(true);
    try {
      const run = await testSemanticIndicator(selectedIndicator.id, {
        sampleRows,
        testedBy: testedBy.trim() || null,
      });
      setLastTestRun(run);
      setTestRuns(await listIndicatorTestRuns(selectedIndicator.id));
    } catch (e2) {
      setTestError(e2?.response?.data?.detail?.message || e2.message);
    } finally {
      setTestSubmitting(false);
    }
  }

  return (
    <AppLayout
      title="Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa"
      subtitle="UC-043 — Tạo chỉ tiêu mới (tên/mô tả/biểu thức/lĩnh vực), hệ thống lưu vào PostgreSQL; kiểm thử chỉ tiêu trên truy vấn mẫu, hệ thống chạy và hiển thị kết quả; quản lý phiên bản chỉ tiêu, hệ thống lưu version + audit."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{info}</span>
        </div>
      )}

      {/* ---------- Tra cứu + Bước 1/3: danh sách và biểu mẫu ---------- */}
      <div style={TWO_COL_GRID}>
        <div className="card">
          <div className="card-header">
            <h2>Danh sách chỉ tiêu</h2>
            <button className="icon-btn" title="Làm mới" onClick={() => loadIndicators(true)}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="card-body">
            <div className="form-grid">
              <div className="field">
                <label htmlFor="domain-filter">Lĩnh vực</label>
                <input
                  id="domain-filter"
                  placeholder="vd Ngân sách, Tài sản..."
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="status-filter">Trạng thái</label>
                <select
                  id="status-filter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">-- Tất cả --</option>
                  {INDICATOR_STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {loading ? (
              <p className="empty-state">Đang tải...</p>
            ) : indicators.length === 0 ? (
              <p className="empty-state">Chưa có chỉ tiêu nào.</p>
            ) : (
              <table className="data-table" style={{ marginTop: 14 }}>
                <thead>
                  <tr>
                    <th>Tên chỉ tiêu</th>
                    <th>Lĩnh vực</th>
                    <th>Trạng thái</th>
                    <th>Phiên bản</th>
                  </tr>
                </thead>
                <tbody>
                  {indicators.map((i) => (
                    <tr
                      key={i.id}
                      onClick={() => setSelectedId(i.id)}
                      style={{
                        cursor: "pointer",
                        background: selectedId === i.id ? "var(--color-primary-soft)" : undefined,
                      }}
                    >
                      <td>
                        <strong>{i.name}</strong>
                        <div style={{ fontSize: 12, color: "var(--color-text-secondary)", fontFamily: "monospace" }}>
                          {i.expression}
                        </div>
                      </td>
                      <td>{i.domain}</td>
                      <td>
                        <span className={statusBadgeClass(i.status)}>{statusLabel(i.status)}</span>
                      </td>
                      <td>v{i.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>{selectedIndicator ? `${selectedIndicator.name} — v${selectedIndicator.version}` : "Tạo chỉ tiêu mới"}</h2>
            <div className="row-actions">
              <button
                className={`btn ${activePanel === "create" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("create")}
              >
                Bước 1 — Tạo mới
              </button>
              <button
                className={`btn ${activePanel === "edit" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActivePanel("edit")}
                disabled={!selectedIndicator}
              >
                Bước 3 — Sửa / phiên bản
              </button>
            </div>
          </div>
          <div className="card-body">
            {activePanel === "create" ? (
              <form onSubmit={handleCreate}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="create-name">Tên chỉ tiêu</label>
                    <input
                      id="create-name"
                      required
                      value={createForm.name}
                      onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="create-domain">Lĩnh vực</label>
                    <input
                      id="create-domain"
                      required
                      placeholder="vd Ngân sách, Tài sản, Giá, Văn bản..."
                      value={createForm.domain}
                      onChange={(e) => setCreateForm((f) => ({ ...f, domain: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="create-expression">Biểu thức</label>
                  <input
                    id="create-expression"
                    required
                    style={{ fontFamily: "monospace" }}
                    placeholder={`vd SUM('so_tien') / COUNT()`}
                    value={createForm.expression}
                    onChange={(e) => setCreateForm((f) => ({ ...f, expression: e.target.value }))}
                  />
                  <small>Hỗ trợ SUM/AVG/COUNT/MIN/MAX kết hợp phép toán số học +-*/.</small>
                </div>

                <div className="field">
                  <label htmlFor="create-description">Mô tả</label>
                  <textarea
                    id="create-description"
                    rows={3}
                    value={createForm.description}
                    onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))}
                  />
                </div>

                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="create-created-by">Người tạo</label>
                    <input
                      id="create-created-by"
                      value={createForm.created_by}
                      onChange={(e) => setCreateForm((f) => ({ ...f, created_by: e.target.value }))}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="create-note">Ghi chú (audit)</label>
                    <input
                      id="create-note"
                      value={createForm.note}
                      onChange={(e) => setCreateForm((f) => ({ ...f, note: e.target.value }))}
                    />
                  </div>
                </div>

                <button className="btn btn-primary" type="submit" disabled={submitting} style={{ marginTop: 14 }}>
                  {submitting ? "Đang lưu..." : "Tạo chỉ tiêu"}
                </button>
              </form>
            ) : selectedIndicator ? (
              <form onSubmit={handleUpdate}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="edit-name">Tên chỉ tiêu</label>
                    <input
                      id="edit-name"
                      value={editForm.name}
                      onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="edit-domain">Lĩnh vực</label>
                    <input
                      id="edit-domain"
                      value={editForm.domain}
                      onChange={(e) => setEditForm((f) => ({ ...f, domain: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="edit-expression">Biểu thức</label>
                  <input
                    id="edit-expression"
                    style={{ fontFamily: "monospace" }}
                    value={editForm.expression}
                    onChange={(e) => setEditForm((f) => ({ ...f, expression: e.target.value }))}
                  />
                </div>

                <div className="field">
                  <label htmlFor="edit-description">Mô tả (để trống để xoá)</label>
                  <textarea
                    id="edit-description"
                    rows={3}
                    value={editForm.description}
                    onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                  />
                </div>

                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="edit-status">Trạng thái</label>
                    <select
                      id="edit-status"
                      value={editForm.status}
                      onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}
                    >
                      {INDICATOR_STATUSES.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="edit-changed-by">Người sửa</label>
                    <input
                      id="edit-changed-by"
                      value={editForm.changed_by}
                      onChange={(e) => setEditForm((f) => ({ ...f, changed_by: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="edit-note">Ghi chú thay đổi (audit)</label>
                  <input
                    id="edit-note"
                    value={editForm.note}
                    onChange={(e) => setEditForm((f) => ({ ...f, note: e.target.value }))}
                  />
                </div>

                <button className="btn btn-primary" type="submit" disabled={submitting} style={{ marginTop: 14 }}>
                  {submitting ? "Đang lưu..." : "Lưu (tăng phiên bản)"}
                </button>
              </form>
            ) : (
              <p className="empty-state">Chọn 1 chỉ tiêu ở danh sách bên trái để sửa.</p>
            )}
          </div>
        </div>
      </div>

      {/* ---------- Bước 2 + lịch sử phiên bản/audit ---------- */}
      {selectedIndicator && (
        <div style={{ ...TWO_COL_GRID_EVEN, marginTop: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2 style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <FlaskConical size={16} />
                Bước 2 — Kiểm thử trên truy vấn mẫu
              </h2>
            </div>
            <div className="card-body">
              {testError && (
                <div className="alert alert-error">
                  <AlertCircle size={16} />
                  <span>{testError}</span>
                </div>
              )}

              <form onSubmit={handleRunTest}>
                <div className="field">
                  <label htmlFor="sample-rows">Tập bản ghi mẫu (JSON)</label>
                  <textarea
                    id="sample-rows"
                    rows={8}
                    style={{ fontFamily: "monospace", fontSize: 13 }}
                    value={sampleRowsText}
                    onChange={(e) => setSampleRowsText(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="tested-by">Người kiểm thử</label>
                  <input id="tested-by" value={testedBy} onChange={(e) => setTestedBy(e.target.value)} />
                </div>
                <button className="btn btn-primary" type="submit" disabled={testSubmitting} style={{ marginTop: 14 }}>
                  {testSubmitting ? "Đang chạy..." : "Chạy kiểm thử"}
                </button>
              </form>

              {lastTestRun && (
                <div
                  style={{
                    marginTop: 18,
                    paddingTop: 14,
                    borderTop: "1px solid var(--color-border)",
                  }}
                >
                  <p style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 6px" }}>
                    <span>Kết quả:</span>
                    <span className={testStatusBadgeClass(lastTestRun.status)}>
                      {lastTestRun.status === "SUCCESS" ? "Thành công" : "Lỗi"}
                    </span>
                  </p>
                  {lastTestRun.status === "SUCCESS" ? (
                    <p style={{ margin: 0 }}>
                      Giá trị kết quả: <strong>{lastTestRun.result_value}</strong>
                    </p>
                  ) : (
                    <p style={{ margin: 0, color: "var(--color-danger)" }}>{lastTestRun.error_message}</p>
                  )}
                </div>
              )}

              {testRuns.length > 0 && (
                <>
                  <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>Lịch sử kiểm thử</h3>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Thời điểm</th>
                        <th>Trạng thái</th>
                        <th>Kết quả</th>
                        <th>Người kiểm thử</th>
                      </tr>
                    </thead>
                    <tbody>
                      {testRuns.map((t) => (
                        <tr key={t.id}>
                          <td>{formatTime(t.tested_at)}</td>
                          <td>
                            <span className={testStatusBadgeClass(t.status)}>
                              {t.status === "SUCCESS" ? "Thành công" : "Lỗi"}
                            </span>
                          </td>
                          <td>{t.status === "SUCCESS" ? t.result_value : t.error_message}</td>
                          <td>{t.tested_by || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <History size={16} />
                Lịch sử phiên bản &amp; nhật ký
              </h2>
            </div>
            <div className="card-body">
              <h3 style={{ marginTop: 0 }}>Phiên bản</h3>
              {versions.length === 0 ? (
                <p className="empty-state">Chưa có lịch sử phiên bản.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>v</th>
                      <th>Tên</th>
                      <th>Biểu thức</th>
                      <th>Trạng thái</th>
                      <th>Thời điểm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versions.map((v) => (
                      <tr key={v.id}>
                        <td>v{v.version}</td>
                        <td>{v.name}</td>
                        <td style={{ fontFamily: "monospace", fontSize: 12 }}>{v.expression}</td>
                        <td>
                          <span className={statusBadgeClass(v.status)}>{statusLabel(v.status)}</span>
                        </td>
                        <td>{formatTime(v.changed_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <h3 style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 6 }}>
                <ScrollText size={14} />
                Nhật ký (audit log)
              </h3>
              {auditLogs.length === 0 ? (
                <p className="empty-state">Chưa có nhật ký.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Hành động</th>
                      <th>Người thực hiện</th>
                      <th>Thời điểm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((a) => (
                      <tr key={a.id}>
                        <td>{a.action}</td>
                        <td>{a.actor || "—"}</td>
                        <td>{formatTime(a.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}