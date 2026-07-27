import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Plug, RefreshCw, Save, XCircle } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import {
  configureKeycloak,
  configureLgsp,
  getKeycloakConfig,
  getLgspConfig,
  recheckKeycloak,
  recheckLgsp,
} from "../api/integrationConfig.js";

const EMPTY_KEYCLOAK = { base_url: "", realm: "", client_id: "" };
const EMPTY_LGSP = { base_url: "", protocol: "" };

function ConnectionStatus({ endpoint }) {
  if (!endpoint) {
    return <span className="badge badge-neutral">Chưa cấu hình</span>;
  }
  return endpoint.is_connected ? (
    <span className="badge badge-success">
      <CheckCircle2 size={13} /> Đã kết nối
    </span>
  ) : (
    <span className="badge badge-danger">
      <XCircle size={13} /> Chưa kết nối
    </span>
  );
}

export default function IntegrationConfigPage() {
  const [keycloak, setKeycloak] = useState(null);
  const [lgsp, setLgsp] = useState(null);
  const [keycloakForm, setKeycloakForm] = useState(EMPTY_KEYCLOAK);
  const [lgspForm, setLgspForm] = useState(EMPTY_LGSP);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingKeycloak, setSavingKeycloak] = useState(false);
  const [savingLgsp, setSavingLgsp] = useState(false);
  const [recheckingKeycloak, setRecheckingKeycloak] = useState(false);
  const [recheckingLgsp, setRecheckingLgsp] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const [kc, lg] = await Promise.all([
        getKeycloakConfig().catch((e) => (e?.response?.status === 404 ? null : Promise.reject(e))),
        getLgspConfig().catch((e) => (e?.response?.status === 404 ? null : Promise.reject(e))),
      ]);
      setKeycloak(kc);
      setLgsp(lg);
      if (kc) {
        setKeycloakForm({
          base_url: kc.base_url,
          realm: kc.extra_config?.realm || "",
          client_id: kc.extra_config?.client_id || "",
        });
      }
      if (lg) {
        setLgspForm({ base_url: lg.base_url, protocol: lg.extra_config?.protocol || "" });
      }
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleSubmitKeycloak(e) {
    e.preventDefault();
    setSavingKeycloak(true);
    setSuccess(null);
    try {
      const data = await configureKeycloak(keycloakForm);
      setKeycloak(data);
      setError(null);
      setSuccess(
        data.is_connected
          ? "Đã lưu cấu hình Keycloak — kiểm tra kết nối: thành công."
          : `Đã lưu cấu hình Keycloak — kiểm tra kết nối: thất bại (${data.last_check_message}).`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSavingKeycloak(false);
    }
  }

  async function handleSubmitLgsp(e) {
    e.preventDefault();
    setSavingLgsp(true);
    setSuccess(null);
    try {
      const data = await configureLgsp(lgspForm);
      setLgsp(data);
      setError(null);
      setSuccess(
        data.is_connected
          ? "Đã lưu cấu hình LGSP — kiểm tra giao thức kết nối: thành công."
          : `Đã lưu cấu hình LGSP — kiểm tra giao thức kết nối: thất bại (${data.last_check_message}).`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSavingLgsp(false);
    }
  }

  async function handleRecheckKeycloak() {
    setRecheckingKeycloak(true);
    try {
      const data = await recheckKeycloak();
      setKeycloak(data);
      setError(null);
      setSuccess(data.is_connected ? "Kiểm tra lại: kết nối thành công." : `Kiểm tra lại: thất bại (${data.last_check_message}).`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRecheckingKeycloak(false);
    }
  }

  async function handleRecheckLgsp() {
    setRecheckingLgsp(true);
    try {
      const data = await recheckLgsp();
      setLgsp(data);
      setError(null);
      setSuccess(data.is_connected ? "Kiểm tra lại: kết nối thành công." : `Kiểm tra lại: thất bại (${data.last_check_message}).`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setRecheckingLgsp(false);
    }
  }

  return (
    <AppLayout
      title="Cấu hình tích hợp"
      subtitle="UC-07 — Cấu hình điểm cuối Keycloak và LGSP; lưu sẽ tự động kiểm tra kết nối/giao thức."
    >
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <CheckCircle2 size={16} />
          <span>{success}</span>
        </div>
      )}

      {loading ? (
        <div className="empty-state">Đang tải dữ liệu...</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Điểm cuối Keycloak</h2>
              <ConnectionStatus endpoint={keycloak} />
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmitKeycloak}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="kc-base-url">URL điểm cuối</label>
                    <input
                      id="kc-base-url"
                      placeholder="https://sso.hungyen.gov.vn"
                      value={keycloakForm.base_url}
                      onChange={(e) => setKeycloakForm({ ...keycloakForm, base_url: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="kc-realm">Realm</label>
                    <input
                      id="kc-realm"
                      value={keycloakForm.realm}
                      onChange={(e) => setKeycloakForm({ ...keycloakForm, realm: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="kc-client-id">Client ID</label>
                    <input
                      id="kc-client-id"
                      value={keycloakForm.client_id}
                      onChange={(e) => setKeycloakForm({ ...keycloakForm, client_id: e.target.value })}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingKeycloak}>
                      <Save size={15} />
                      {savingKeycloak ? "Đang lưu..." : "Lưu + kiểm tra kết nối"}
                    </button>
                    {keycloak && (
                      <button
                        type="button"
                        className="btn"
                        onClick={handleRecheckKeycloak}
                        disabled={recheckingKeycloak}
                      >
                        <RefreshCw size={15} />
                        {recheckingKeycloak ? "Đang kiểm tra..." : "Kiểm tra lại"}
                      </button>
                    )}
                  </div>
                  {keycloak?.last_checked_at && (
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Kiểm tra lần cuối: {new Date(keycloak.last_checked_at).toLocaleString("vi-VN")} —{" "}
                      {keycloak.last_check_message}
                    </div>
                  )}
                </div>
              </form>
            </div>
          </div>

          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Điểm cuối LGSP</h2>
              <ConnectionStatus endpoint={lgsp} />
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmitLgsp}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="lgsp-base-url">URL điểm cuối</label>
                    <input
                      id="lgsp-base-url"
                      placeholder="https://lgsp.hungyen.gov.vn"
                      value={lgspForm.base_url}
                      onChange={(e) => setLgspForm({ ...lgspForm, base_url: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="lgsp-protocol">Giao thức kết nối</label>
                    <select
                      id="lgsp-protocol"
                      value={lgspForm.protocol}
                      onChange={(e) => setLgspForm({ ...lgspForm, protocol: e.target.value })}
                    >
                      <option value="">-- Chọn giao thức --</option>
                      <option value="REST">REST</option>
                      <option value="SOAP">SOAP</option>
                    </select>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingLgsp}>
                      <Plug size={15} />
                      {savingLgsp ? "Đang lưu..." : "Lưu + kiểm tra giao thức"}
                    </button>
                    {lgsp && (
                      <button type="button" className="btn" onClick={handleRecheckLgsp} disabled={recheckingLgsp}>
                        <RefreshCw size={15} />
                        {recheckingLgsp ? "Đang kiểm tra..." : "Kiểm tra lại"}
                      </button>
                    )}
                  </div>
                  {lgsp?.last_checked_at && (
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Kiểm tra lần cuối: {new Date(lgsp.last_checked_at).toLocaleString("vi-VN")} —{" "}
                      {lgsp.last_check_message}
                    </div>
                  )}
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}