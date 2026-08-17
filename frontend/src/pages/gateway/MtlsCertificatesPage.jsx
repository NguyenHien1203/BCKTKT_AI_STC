import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import AppLayout from "../../components/AppLayout.jsx";
import {
  checkCertificateRevoked,
  getCertificateRevocationList,
  listMtlsCertificates,
  registerMtlsCertificate,
  revokeMtlsCertificate,
  rotateMtlsCertificate,
} from "../../api/mtlsCertificates.js";

function formatTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("vi-VN");
}

const STATUS_LABEL = {
  ACTIVE: "Đang hiệu lực",
  ROTATED: "Đã luân chuyển",
  REVOKED: "Đã thu hồi",
};

const STATUS_BADGE_CLASS = {
  ACTIVE: "badge-success",
  ROTATED: "badge-warning",
  REVOKED: "badge-danger",
};

const EMPTY_REGISTER_FORM = {
  consumer_code: "",
  consumer_name: "",
  common_name: "",
  serial_number: "",
  pem_certificate: "",
  not_before: "",
  not_after: "",
};

const EMPTY_ROTATE_FORM = {
  common_name: "",
  serial_number: "",
  pem_certificate: "",
  not_before: "",
  not_after: "",
};

function DetailRow({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 8, fontSize: 13, padding: "4px 0" }}>
      <span style={{ color: "var(--color-text-secondary)", minWidth: 150, flexShrink: 0 }}>
        {label}
      </span>
      <span style={{ wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}

export default function MtlsCertificatesPage() {
  const [certificates, setCertificates] = useState([]);
  const [consumerCodeFilter, setConsumerCodeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const [crl, setCrl] = useState([]);
  const [crlConsumerFilter, setCrlConsumerFilter] = useState("");
  const [checkSerial, setCheckSerial] = useState("");
  const [checkResult, setCheckResult] = useState(null);

  const [registerForm, setRegisterForm] = useState(EMPTY_REGISTER_FORM);
  const [rotateForm, setRotateForm] = useState(EMPTY_ROTATE_FORM);
  const [revokeReason, setRevokeReason] = useState("");

  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedCertificate = certificates.find((c) => c.id === selectedId) || null;

  async function loadCertificates(keepSelection = true) {
    setLoading(true);
    try {
      const data = await listMtlsCertificates({
        consumerCode: consumerCodeFilter || null,
        status: statusFilter || null,
      });
      const safeData = Array.isArray(data) ? data : [];
      setCertificates(safeData);
      if (!keepSelection || !safeData.some((c) => c.id === selectedId)) {
        setSelectedId(safeData.length > 0 ? safeData[0].id : null);
      }
    } catch (err) {
      setCertificates([]);
      setError(err?.response?.data?.detail?.message || "Không tải được danh sách chứng thư");
    } finally {
      setLoading(false);
    }
  }

  async function loadCrl() {
    try {
      const data = await getCertificateRevocationList({
        consumerCode: crlConsumerFilter || null,
      });
      setCrl(Array.isArray(data) ? data : []);
    } catch {
      setCrl([]);
    }
  }

  useEffect(() => {
    loadCertificates(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consumerCodeFilter, statusFilter]);

  useEffect(() => {
    loadCrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [crlConsumerFilter]);

  function clearMessages() {
    setError(null);
    setInfo(null);
  }

  // ------------------------------------------------------------------
  // Bước 1 — Đăng ký chứng thư -> hệ thống lưu vào kho tin cậy.
  // ------------------------------------------------------------------
  async function handleRegister(e) {
    e.preventDefault();
    clearMessages();
    setSubmitting(true);
    try {
      await registerMtlsCertificate({
        ...registerForm,
        not_before: new Date(registerForm.not_before).toISOString(),
        not_after: new Date(registerForm.not_after).toISOString(),
      });
      setInfo("Đã đăng ký chứng thư vào kho tin cậy.");
      setRegisterForm(EMPTY_REGISTER_FORM);
      await loadCertificates(false);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Đăng ký chứng thư thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // ------------------------------------------------------------------
  // Bước 2 — Luân chuyển chứng thư -> hệ thống cập nhật.
  // ------------------------------------------------------------------
  async function handleRotate(e) {
    e.preventDefault();
    if (!selectedCertificate) return;
    clearMessages();
    setSubmitting(true);
    try {
      await rotateMtlsCertificate(selectedCertificate.id, {
        ...rotateForm,
        not_before: new Date(rotateForm.not_before).toISOString(),
        not_after: new Date(rotateForm.not_after).toISOString(),
      });
      setInfo(`Đã luân chuyển chứng thư #${selectedCertificate.id} sang chứng thư mới.`);
      setRotateForm(EMPTY_ROTATE_FORM);
      await loadCertificates(false);
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Luân chuyển chứng thư thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  // ------------------------------------------------------------------
  // Bước 3 — Thu hồi chứng thư -> hệ thống thêm vào CRL.
  // ------------------------------------------------------------------
  async function handleRevoke() {
    if (!selectedCertificate) return;
    clearMessages();
    setSubmitting(true);
    try {
      await revokeMtlsCertificate(selectedCertificate.id, revokeReason);
      setInfo(`Đã thu hồi chứng thư #${selectedCertificate.id} và thêm vào CRL.`);
      setRevokeReason("");
      await loadCertificates(true);
      await loadCrl();
    } catch (err) {
      setError(err?.response?.data?.detail?.message || "Thu hồi chứng thư thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCheckRevoked() {
    if (!checkSerial.trim()) return;
    clearMessages();
    try {
      const data = await checkCertificateRevoked(checkSerial.trim());
      setCheckResult(data);
    } catch (err) {
      setCheckResult(null);
      setError(err?.response?.data?.detail?.message || "Kiểm tra CRL thất bại");
    }
  }

  return (
    <AppLayout
      title="Quản lý chứng thư / mTLS cho đơn vị khai thác"
      subtitle="UC-062 — (1) Đăng ký chứng thư của đơn vị khai thác, hệ thống lưu vào kho tin cậy. (2) Luân chuyển chứng thư, hệ thống cập nhật. (3) Thu hồi chứng thư, hệ thống thêm vào CRL."
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

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
        {/* ---------- Cột trái: kho tin cậy + đăng ký chứng thư mới ---------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2>Kho tin cậy — Chứng thư mTLS</h2>
              <button className="icon-btn" title="Tải lại" onClick={() => loadCertificates(false)}>
                <RefreshCw size={15} />
              </button>
            </div>
            <div className="card-body">
              <div className="form-grid" style={{ marginBottom: 16 }}>
                <div className="field">
                  <label htmlFor="consumer-filter">Lọc theo mã đơn vị khai thác</label>
                  <input
                    id="consumer-filter"
                    value={consumerCodeFilter}
                    onChange={(e) => setConsumerCodeFilter(e.target.value)}
                    placeholder="vd: DVKT-001"
                  />
                </div>
                <div className="field">
                  <label htmlFor="status-filter">Trạng thái</label>
                  <select
                    id="status-filter"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="">Tất cả trạng thái</option>
                    <option value="ACTIVE">Đang hiệu lực</option>
                    <option value="ROTATED">Đã luân chuyển</option>
                    <option value="REVOKED">Đã thu hồi</option>
                  </select>
                </div>
              </div>

              {loading && <p>Đang tải…</p>}
              {!loading && certificates.length === 0 && (
                <div className="empty-state">Chưa có chứng thư nào.</div>
              )}

              {!loading && certificates.length > 0 && (
                <div style={{ maxHeight: 420, overflowY: "auto" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Đơn vị khai thác</th>
                        <th>CN / Số hiệu</th>
                        <th>Trạng thái</th>
                        <th>Hết hạn</th>
                      </tr>
                    </thead>
                    <tbody>
                      {certificates.map((c) => (
                        <tr
                          key={c.id}
                          onClick={() => setSelectedId(c.id)}
                          style={{
                            cursor: "pointer",
                            background:
                              c.id === selectedId ? "var(--color-primary-soft)" : undefined,
                          }}
                        >
                          <td>
                            <div>
                              <strong>{c.consumer_name}</strong>
                            </div>
                            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                              {c.consumer_code}
                            </div>
                          </td>
                          <td>
                            <div>{c.common_name}</div>
                            <div
                              style={{
                                fontFamily: "monospace",
                                fontSize: 12,
                                color: "var(--color-text-secondary)",
                              }}
                            >
                              {c.serial_number}
                            </div>
                          </td>
                          <td>
                            <span className={`badge ${STATUS_BADGE_CLASS[c.status] || "badge-neutral"}`}>
                              {STATUS_LABEL[c.status] || c.status}
                            </span>
                          </td>
                          <td style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                            {formatTime(c.not_after)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Bước 1 — form đăng ký chứng thư mới */}
          <div className="card">
            <div className="card-header">
              <h2>Bước 1 — Đăng ký chứng thư mới</h2>
            </div>
            <div className="card-body">
              <form onSubmit={handleRegister} className="form-grid">
                <div className="field">
                  <label htmlFor="r-consumer-code">Mã đơn vị khai thác *</label>
                  <input
                    id="r-consumer-code"
                    required
                    value={registerForm.consumer_code}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, consumer_code: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-consumer-name">Tên đơn vị khai thác *</label>
                  <input
                    id="r-consumer-name"
                    required
                    value={registerForm.consumer_name}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, consumer_name: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-cn">Common Name (CN) *</label>
                  <input
                    id="r-cn"
                    required
                    value={registerForm.common_name}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, common_name: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-serial">Số hiệu chứng thư *</label>
                  <input
                    id="r-serial"
                    required
                    value={registerForm.serial_number}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, serial_number: e.target.value })
                    }
                  />
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="r-pem">Chứng thư PEM *</label>
                  <textarea
                    id="r-pem"
                    required
                    rows={4}
                    style={{ fontFamily: "monospace", fontSize: 12 }}
                    placeholder="-----BEGIN CERTIFICATE-----..."
                    value={registerForm.pem_certificate}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, pem_certificate: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-not-before">Hiệu lực từ *</label>
                  <input
                    id="r-not-before"
                    required
                    type="datetime-local"
                    value={registerForm.not_before}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, not_before: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="r-not-after">Hết hạn *</label>
                  <input
                    id="r-not-after"
                    required
                    type="datetime-local"
                    value={registerForm.not_after}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, not_after: e.target.value })
                    }
                  />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    Đăng ký chứng thư
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* ---------- Cột phải: chi tiết + luân chuyển + thu hồi + CRL ---------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h2>Chứng thư đang chọn</h2>
            </div>
            <div className="card-body">
              {!selectedCertificate && <p>Chọn 1 chứng thư ở danh sách bên trái.</p>}
              {selectedCertificate && (
                <div>
                  <DetailRow
                    label="Đơn vị"
                    value={`${selectedCertificate.consumer_name} (${selectedCertificate.consumer_code})`}
                  />
                  <DetailRow label="CN" value={selectedCertificate.common_name} />
                  <DetailRow label="Số hiệu" value={selectedCertificate.serial_number} />
                  <DetailRow
                    label="Vân tay (SHA-256)"
                    value={
                      <span style={{ fontFamily: "monospace", fontSize: 12 }}>
                        {selectedCertificate.fingerprint_sha256}
                      </span>
                    }
                  />
                  <DetailRow
                    label="Trạng thái"
                    value={
                      <span
                        className={`badge ${
                          STATUS_BADGE_CLASS[selectedCertificate.status] || "badge-neutral"
                        }`}
                      >
                        {STATUS_LABEL[selectedCertificate.status] || selectedCertificate.status}
                      </span>
                    }
                  />
                  <DetailRow
                    label="Hiệu lực"
                    value={`${formatTime(selectedCertificate.not_before)} → ${formatTime(
                      selectedCertificate.not_after
                    )}`}
                  />
                  {selectedCertificate.rotated_to_id && (
                    <DetailRow
                      label="Đã luân chuyển sang"
                      value={`#${selectedCertificate.rotated_to_id}`}
                    />
                  )}
                  {selectedCertificate.status === "REVOKED" && (
                    <DetailRow
                      label="Lý do thu hồi"
                      value={`${selectedCertificate.revocation_reason || "—"} (${formatTime(
                        selectedCertificate.revoked_at
                      )})`}
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {selectedCertificate && selectedCertificate.status === "ACTIVE" && (
            <>
              {/* Bước 2 — luân chuyển */}
              <div className="card">
                <div className="card-header">
                  <h2>Bước 2 — Luân chuyển chứng thư</h2>
                </div>
                <div className="card-body">
                  <form onSubmit={handleRotate} className="form-grid">
                    <div className="field">
                      <label htmlFor="rot-cn">Common Name (CN) chứng thư mới *</label>
                      <input
                        id="rot-cn"
                        required
                        value={rotateForm.common_name}
                        onChange={(e) =>
                          setRotateForm({ ...rotateForm, common_name: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rot-serial">Số hiệu chứng thư mới *</label>
                      <input
                        id="rot-serial"
                        required
                        value={rotateForm.serial_number}
                        onChange={(e) =>
                          setRotateForm({ ...rotateForm, serial_number: e.target.value })
                        }
                      />
                    </div>
                    <div className="field" style={{ gridColumn: "1 / -1" }}>
                      <label htmlFor="rot-pem">Chứng thư PEM mới *</label>
                      <textarea
                        id="rot-pem"
                        required
                        rows={3}
                        style={{ fontFamily: "monospace", fontSize: 12 }}
                        placeholder="-----BEGIN CERTIFICATE-----..."
                        value={rotateForm.pem_certificate}
                        onChange={(e) =>
                          setRotateForm({ ...rotateForm, pem_certificate: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rot-not-before">Hiệu lực từ *</label>
                      <input
                        id="rot-not-before"
                        required
                        type="datetime-local"
                        value={rotateForm.not_before}
                        onChange={(e) =>
                          setRotateForm({ ...rotateForm, not_before: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rot-not-after">Hết hạn *</label>
                      <input
                        id="rot-not-after"
                        required
                        type="datetime-local"
                        value={rotateForm.not_after}
                        onChange={(e) =>
                          setRotateForm({ ...rotateForm, not_after: e.target.value })
                        }
                      />
                    </div>
                    <div style={{ gridColumn: "1 / -1" }}>
                      <button type="submit" className="btn" disabled={submitting}>
                        Luân chuyển
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              {/* Bước 3 — thu hồi */}
              <div className="card">
                <div className="card-header">
                  <h2>Bước 3 — Thu hồi chứng thư</h2>
                </div>
                <div className="card-body">
                  <div className="form-grid">
                    <div className="field" style={{ gridColumn: "1 / -1" }}>
                      <label htmlFor="revoke-reason">Lý do thu hồi (tuỳ chọn)</label>
                      <input
                        id="revoke-reason"
                        value={revokeReason}
                        onChange={(e) => setRevokeReason(e.target.value)}
                      />
                    </div>
                    <div style={{ gridColumn: "1 / -1" }}>
                      <button
                        type="button"
                        className="btn btn-danger-ghost"
                        disabled={submitting}
                        onClick={handleRevoke}
                      >
                        <ShieldAlert size={15} />
                        Thu hồi + thêm vào CRL
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* CRL */}
          <div className="card">
            <div className="card-header">
              <h2>
                <ShieldCheck size={15} style={{ verticalAlign: "middle", marginRight: 6 }} />
                CRL — Danh sách chứng thư đã thu hồi
              </h2>
            </div>
            <div className="card-body">
              <div className="field" style={{ marginBottom: 16 }}>
                <label htmlFor="crl-filter">Lọc theo mã đơn vị khai thác</label>
                <input
                  id="crl-filter"
                  value={crlConsumerFilter}
                  onChange={(e) => setCrlConsumerFilter(e.target.value)}
                  placeholder="vd: DVKT-001"
                />
              </div>

              {crl.length === 0 ? (
                <div className="empty-state">CRL hiện đang trống.</div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Số hiệu</th>
                      <th>Đơn vị</th>
                      <th>Lý do</th>
                      <th>Thời điểm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {crl.map((entry) => (
                      <tr key={entry.id}>
                        <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                          {entry.serial_number}
                        </td>
                        <td>{entry.consumer_code}</td>
                        <td>{entry.reason || "—"}</td>
                        <td style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                          {formatTime(entry.revoked_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <div className="form-grid" style={{ marginTop: 16 }}>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="check-serial">Kiểm tra 1 số hiệu chứng thư có trong CRL</label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      id="check-serial"
                      style={{ flex: 1 }}
                      value={checkSerial}
                      onChange={(e) => setCheckSerial(e.target.value)}
                      placeholder="Nhập số hiệu chứng thư"
                    />
                    <button type="button" className="btn btn-secondary" onClick={handleCheckRevoked}>
                      Kiểm tra
                    </button>
                  </div>
                </div>
              </div>
              {checkResult && (
                <p style={{ fontSize: 13, marginTop: 8 }}>
                  {checkResult.serial_number}:{" "}
                  {checkResult.is_revoked ? (
                    <span style={{ fontWeight: 600, color: "var(--color-danger)" }}>
                      Đã bị thu hồi
                    </span>
                  ) : (
                    <span style={{ fontWeight: 600, color: "var(--color-success)" }}>
                      Chưa bị thu hồi
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}