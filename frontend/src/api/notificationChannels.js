import { authIdentityClient } from "./orgUnits";

export async function listNotificationChannels() {
  const { data } = await authIdentityClient.get("/notification-channels");
  return data;
}

export async function getSmtpConfig() {
  const { data } = await authIdentityClient.get("/notification-channels/smtp");
  return data;
}

export async function configureSmtp(payload) {
  const { data } = await authIdentityClient.put("/notification-channels/smtp", payload);
  return data;
}

export async function sendSmtpTest(recipient) {
  const { data } = await authIdentityClient.post("/notification-channels/smtp/test", { recipient });
  return data;
}

export async function getSmsConfig() {
  const { data } = await authIdentityClient.get("/notification-channels/sms");
  return data;
}

export async function configureSms(payload) {
  const { data } = await authIdentityClient.put("/notification-channels/sms", payload);
  return data;
}

export async function sendSmsTest(recipient) {
  const { data } = await authIdentityClient.post("/notification-channels/sms/test", { recipient });
  return data;
}

export async function getWebhookConfig() {
  const { data } = await authIdentityClient.get("/notification-channels/webhook");
  return data;
}

export async function configureWebhook(payload) {
  const { data } = await authIdentityClient.put("/notification-channels/webhook", payload);
  return data;
}

export async function sendWebhookTest() {
  const { data } = await authIdentityClient.post("/notification-channels/webhook/test", {});
  return data;
}