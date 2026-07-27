import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Mail, MessageSquare, Send, Webhook, XCircle } from "lucide-react";
import AppLayout from "../components/AppLayout.jsx";
import {
  configureSmtp,
  configureSms,
  configureWebhook,
  getSmtpConfig,
  getSmsConfig,
  getWebhookConfig,
  sendSmtpTest,
  sendSmsTest,
  sendWebhookTest,
} from "../api/notificationChannels.js";

const EMPTY_SMTP = { smtp_host: "", smtp_port: 587, from_email: "", username: "", password: "" };
const EMPTY_SMS = { gateway_url: "", api_key: "" };
const EMPTY_WEBHOOK = { webhook_url: "" };

function ChannelStatus({ channel }) {
  if (!channel) {
    return <span className="badge badge-neutral">Chưa cấu hình</span>;
  }
  return channel.is_verified ? (
    <span className="badge badge-success">
      <CheckCircle2 size={13} /> Đã kiểm thử thành công
    </span>
  ) : (
    <span className="badge badge-danger">
      <XCircle size={13} /> Chưa kiểm thử / thất bại
    </span>
  );
}

export default function NotificationChannelsPage() {
  const [smtp, setSmtp] = useState(null);
  const [sms, setSms] = useState(null);
  const [webhook, setWebhook] = useState(null);

  const [smtpForm, setSmtpForm] = useState(EMPTY_SMTP);
  const [smsForm, setSmsForm] = useState(EMPTY_SMS);
  const [webhookForm, setWebhookForm] = useState(EMPTY_WEBHOOK);

  const [smtpTestRecipient, setSmtpTestRecipient] = useState("");
  const [smsTestRecipient, setSmsTestRecipient] = useState("");

  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(true);

  const [savingSmtp, setSavingSmtp] = useState(false);
  const [savingSms, setSavingSms] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);
  const [testingSms, setTestingSms] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const notFoundToNull = (e) => (e?.response?.status === 404 ? null : Promise.reject(e));
      const [sm, ss, wh] = await Promise.all([
        getSmtpConfig().catch(notFoundToNull),
        getSmsConfig().catch(notFoundToNull),
        getWebhookConfig().catch(notFoundToNull),
      ]);
      setSmtp(sm);
      setSms(ss);
      setWebhook(wh);
      if (sm) {
        setSmtpForm({
          smtp_host: sm.config?.smtp_host || "",
          smtp_port: sm.config?.smtp_port || 587,
          from_email: sm.config?.from_email || "",
          username: sm.config?.username || "",
          password: sm.config?.password || "",
        });
      }
      if (ss) {
        setSmsForm({ gateway_url: ss.config?.gateway_url || "", api_key: ss.config?.api_key || "" });
      }
      if (wh) {
        setWebhookForm({ webhook_url: wh.config?.webhook_url || "" });
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

  async function handleSubmitSmtp(e) {
    e.preventDefault();
    setSavingSmtp(true);
    setSuccess(null);
    try {
      const data = await configureSmtp({ ...smtpForm, test_recipient: smtpTestRecipient });
      setSmtp(data);
      setError(null);
      setSuccess(
        data.is_verified
          ? "Đã lưu cấu hình SMTP — gửi email kiểm thử: thành công."
          : `Đã lưu cấu hình SMTP — gửi email kiểm thử: thất bại (${data.last_test_message}).`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSavingSmtp(false);
    }
  }

  async function handleTestSmtp() {
    setTestingSmtp(true);
    try {
      const data = await sendSmtpTest(smtpTestRecipient);
      setSmtp(data);
      setError(null);
      setSuccess(data.is_verified ? "Gửi email kiểm thử: thành công." : `Gửi email kiểm thử: thất bại (${data.last_test_message}).`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setTestingSmtp(false);
    }
  }

  async function handleSubmitSms(e) {
    e.preventDefault();
    setSavingSms(true);
    setSuccess(null);
    try {
      const data = await configureSms({ ...smsForm, test_recipient: smsTestRecipient });
      setSms(data);
      setError(null);
      setSuccess(
        data.is_verified
          ? "Đã lưu cấu hình SMS — gửi SMS kiểm thử: thành công."
          : `Đã lưu cấu hình SMS — gửi SMS kiểm thử: thất bại (${data.last_test_message}).`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSavingSms(false);
    }
  }

  async function handleTestSms() {
    setTestingSms(true);
    try {
      const data = await sendSmsTest(smsTestRecipient);
      setSms(data);
      setError(null);
      setSuccess(data.is_verified ? "Gửi SMS kiểm thử: thành công." : `Gửi SMS kiểm thử: thất bại (${data.last_test_message}).`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setTestingSms(false);
    }
  }

  async function handleSubmitWebhook(e) {
    e.preventDefault();
    setSavingWebhook(true);
    setSuccess(null);
    try {
      const data = await configureWebhook(webhookForm);
      setWebhook(data);
      setError(null);
      setSuccess(
        data.is_verified
          ? "Đã lưu cấu hình Webhook — gửi tin nhắn kiểm thử: thành công."
          : `Đã lưu cấu hình Webhook — gửi tin nhắn kiểm thử: thất bại (${data.last_test_message}).`
      );
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setSavingWebhook(false);
    }
  }

  async function handleTestWebhook() {
    setTestingWebhook(true);
    try {
      const data = await sendWebhookTest();
      setWebhook(data);
      setError(null);
      setSuccess(data.is_verified ? "Gửi tin nhắn kiểm thử: thành công." : `Gửi tin nhắn kiểm thử: thất bại (${data.last_test_message}).`);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setTestingWebhook(false);
    }
  }

  return (
    <AppLayout
      title="Cấu hình kênh thông báo"
      subtitle="UC-08 — Cấu hình máy chủ SMTP, cổng SMS, Webhook/Slack; lưu sẽ tự động gửi thông điệp kiểm thử."
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
          {/* ---------- SMTP ---------- */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>
                <Mail size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
                Máy chủ SMTP (email)
              </h2>
              <ChannelStatus channel={smtp} />
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmitSmtp}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="smtp-host">Máy chủ SMTP</label>
                    <input
                      id="smtp-host"
                      placeholder="smtp.hungyen.gov.vn"
                      value={smtpForm.smtp_host}
                      onChange={(e) => setSmtpForm({ ...smtpForm, smtp_host: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="smtp-port">Cổng</label>
                    <input
                      id="smtp-port"
                      type="number"
                      min={1}
                      max={65535}
                      value={smtpForm.smtp_port}
                      onChange={(e) => setSmtpForm({ ...smtpForm, smtp_port: Number(e.target.value) })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="smtp-from">Email gửi (from)</label>
                    <input
                      id="smtp-from"
                      placeholder="noreply@hungyen.gov.vn"
                      value={smtpForm.from_email}
                      onChange={(e) => setSmtpForm({ ...smtpForm, from_email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="smtp-username">Tên đăng nhập (tuỳ chọn)</label>
                    <input
                      id="smtp-username"
                      value={smtpForm.username}
                      onChange={(e) => setSmtpForm({ ...smtpForm, username: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="smtp-password">Mật khẩu (tuỳ chọn)</label>
                    <input
                      id="smtp-password"
                      type="password"
                      value={smtpForm.password}
                      onChange={(e) => setSmtpForm({ ...smtpForm, password: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="smtp-test-recipient">Email nhận thử (bỏ trống = gửi về chính from_email)</label>
                    <input
                      id="smtp-test-recipient"
                      placeholder="admin@hungyen.gov.vn"
                      value={smtpTestRecipient}
                      onChange={(e) => setSmtpTestRecipient(e.target.value)}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingSmtp}>
                      <Send size={15} />
                      {savingSmtp ? "Đang lưu..." : "Lưu + gửi email kiểm thử"}
                    </button>
                    {smtp && (
                      <button type="button" className="btn" onClick={handleTestSmtp} disabled={testingSmtp}>
                        <Send size={15} />
                        {testingSmtp ? "Đang gửi..." : "Gửi thử lại"}
                      </button>
                    )}
                  </div>
                  {smtp?.last_test_at && (
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Gửi thử lần cuối: {new Date(smtp.last_test_at).toLocaleString("vi-VN")} — {smtp.last_test_message}
                    </div>
                  )}
                </div>
              </form>
            </div>
          </div>

          {/* ---------- SMS ---------- */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>
                <MessageSquare size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
                Cổng SMS
              </h2>
              <ChannelStatus channel={sms} />
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmitSms}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="sms-gateway-url">URL cổng SMS</label>
                    <input
                      id="sms-gateway-url"
                      placeholder="https://sms.hungyen.gov.vn/api"
                      value={smsForm.gateway_url}
                      onChange={(e) => setSmsForm({ ...smsForm, gateway_url: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="sms-api-key">API key</label>
                    <input
                      id="sms-api-key"
                      value={smsForm.api_key}
                      onChange={(e) => setSmsForm({ ...smsForm, api_key: e.target.value })}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="sms-test-recipient">Số điện thoại nhận thử</label>
                    <input
                      id="sms-test-recipient"
                      placeholder="0912345678"
                      value={smsTestRecipient}
                      onChange={(e) => setSmsTestRecipient(e.target.value)}
                      required
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingSms}>
                      <Send size={15} />
                      {savingSms ? "Đang lưu..." : "Lưu + gửi SMS kiểm thử"}
                    </button>
                    {sms && (
                      <button
                        type="button"
                        className="btn"
                        onClick={handleTestSms}
                        disabled={testingSms || !smsTestRecipient}
                      >
                        <Send size={15} />
                        {testingSms ? "Đang gửi..." : "Gửi thử lại"}
                      </button>
                    )}
                  </div>
                  {sms?.last_test_at && (
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Gửi thử lần cuối: {new Date(sms.last_test_at).toLocaleString("vi-VN")} — {sms.last_test_message}
                    </div>
                  )}
                </div>
              </form>
            </div>
          </div>

          {/* ---------- Webhook / Slack ---------- */}
          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>
                <Webhook size={16} style={{ verticalAlign: "-2px", marginRight: 6 }} />
                Webhook / Slack
              </h2>
              <ChannelStatus channel={webhook} />
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmitWebhook}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="webhook-url">URL Webhook</label>
                    <input
                      id="webhook-url"
                      placeholder="https://hooks.slack.com/services/..."
                      value={webhookForm.webhook_url}
                      onChange={(e) => setWebhookForm({ webhook_url: e.target.value })}
                      required
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingWebhook}>
                      <Send size={15} />
                      {savingWebhook ? "Đang lưu..." : "Lưu + gửi tin nhắn kiểm thử"}
                    </button>
                    {webhook && (
                      <button type="button" className="btn" onClick={handleTestWebhook} disabled={testingWebhook}>
                        <Send size={15} />
                        {testingWebhook ? "Đang gửi..." : "Gửi thử lại"}
                      </button>
                    )}
                  </div>
                  {webhook?.last_test_at && (
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                      Gửi thử lần cuối: {new Date(webhook.last_test_at).toLocaleString("vi-VN")} — {webhook.last_test_message}
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