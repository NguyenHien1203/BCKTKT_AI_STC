"""Implementation của cổng `AlertDispatcher` — UC-052 bước 3: "Khi vượt
ngưỡng -> Hệ thống gửi cảnh báo qua kênh đã chọn".

`CompositeAlertDispatcher` gửi thật theo `channel_type`:
  - EMAIL: gửi qua SMTP, đọc cấu hình từ biến môi trường `ALERT_SMTP_*`
    (mặc định tái sử dụng cùng máy chủ SMTP với `REPORT_SMTP_*` của
    UC-051 nếu `ALERT_SMTP_HOST` chưa đặt riêng — tránh phải cấu hình 2
    lần cùng 1 SMTP server).
  - SLACK: POST JSON `{"text": message}` tới Slack Incoming Webhook URL
    (`destination`).
  - WEBHOOK: POST JSON `{"subject": subject, "message": message}` tới URL
    tuỳ ý (`destination`).

`InMemoryAlertDispatcher` dùng cho dev/test khi chưa bật
`ALERT_DISPATCH_ENABLED=true` — không gọi mạng, chỉ ghi lại (in-memory)
để kiểm tra trong test, KHÔNG thay thế cho `CompositeAlertDispatcher` khi
triển khai thật.
"""
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import List

import requests

from app.domain.exceptions import AlertDispatchFailed
from app.domain.repositories import AlertDispatcher


class AlertSmtpConfig:
    HOST: str = os.getenv("ALERT_SMTP_HOST", os.getenv("REPORT_SMTP_HOST", ""))
    PORT: int = int(os.getenv("ALERT_SMTP_PORT", os.getenv("REPORT_SMTP_PORT", "587")))
    USERNAME: str = os.getenv("ALERT_SMTP_USERNAME", os.getenv("REPORT_SMTP_USERNAME", ""))
    PASSWORD: str = os.getenv("ALERT_SMTP_PASSWORD", os.getenv("REPORT_SMTP_PASSWORD", ""))
    USE_TLS: bool = os.getenv(
        "ALERT_SMTP_USE_TLS", os.getenv("REPORT_SMTP_USE_TLS", "true")
    ).lower() == "true"
    FROM_ADDRESS: str = os.getenv(
        "ALERT_SMTP_FROM", os.getenv("REPORT_SMTP_FROM", "canh-bao@stc.gov.vn")
    )


WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("ALERT_WEBHOOK_TIMEOUT_SECONDS", "10"))


class CompositeAlertDispatcher(AlertDispatcher):
    """Gửi cảnh báo thật theo từng loại kênh — chỉ nên dùng khi
    `ALERT_DISPATCH_ENABLED=true` (xem factory `get_alert_dispatcher()`).
    """

    def __init__(self, smtp_config: AlertSmtpConfig = AlertSmtpConfig):
        self._smtp_config = smtp_config

    def dispatch(self, channel_type: str, destination: str, subject: str, message: str) -> None:
        if channel_type == "EMAIL":
            self._send_email(destination, subject, message)
        elif channel_type == "SLACK":
            self._post_json(destination, {"text": f"*{subject}*\n{message}"})
        elif channel_type == "WEBHOOK":
            self._post_json(destination, {"subject": subject, "message": message})
        else:
            raise AlertDispatchFailed(f"Loại kênh '{channel_type}' không được hỗ trợ")

    def _send_email(self, to_email: str, subject: str, body_text: str) -> None:
        mime_message = MIMEText(body_text, "plain", "utf-8")
        mime_message["From"] = self._smtp_config.FROM_ADDRESS
        mime_message["To"] = to_email
        mime_message["Subject"] = subject
        try:
            with smtplib.SMTP(
                self._smtp_config.HOST, self._smtp_config.PORT, timeout=20
            ) as server:
                if self._smtp_config.USE_TLS:
                    server.starttls()
                if self._smtp_config.USERNAME:
                    server.login(self._smtp_config.USERNAME, self._smtp_config.PASSWORD)
                server.sendmail(
                    self._smtp_config.FROM_ADDRESS, [to_email], mime_message.as_string()
                )
        except (smtplib.SMTPException, OSError) as exc:
            raise AlertDispatchFailed(
                f"Không gửi được cảnh báo qua email ({self._smtp_config.HOST}): {exc}"
            ) from exc

    @staticmethod
    def _post_json(url: str, payload: dict) -> None:
        try:
            response = requests.post(url, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AlertDispatchFailed(f"Không gửi được cảnh báo tới webhook '{url}': {exc}") from exc


@dataclass
class _SentAlertRecord:
    channel_type: str
    destination: str
    subject: str
    message: str


class InMemoryAlertDispatcher(AlertDispatcher):
    """Dùng cho dev/test khi chưa bật `ALERT_DISPATCH_ENABLED=true` —
    không gọi mạng, chỉ ghi lại (in-memory) để kiểm tra trong test, KHÔNG
    thay thế cho `CompositeAlertDispatcher` khi triển khai thật."""

    def __init__(self):
        self.sent_alerts: List[_SentAlertRecord] = []

    def dispatch(self, channel_type: str, destination: str, subject: str, message: str) -> None:
        self.sent_alerts.append(
            _SentAlertRecord(
                channel_type=channel_type,
                destination=destination,
                subject=subject,
                message=message,
            )
        )


_inmemory_singleton = InMemoryAlertDispatcher()

ALERT_DISPATCH_ENABLED = os.getenv("ALERT_DISPATCH_ENABLED", "false").lower() == "true"


def get_alert_dispatcher() -> AlertDispatcher:
    """Mặc định TẮT gửi thật (`ALERT_DISPATCH_ENABLED=false`) để tránh gọi
    mạng ngoài ý muốn lúc `pytest`/dev nhanh — bật `true` khi triển khai
    thật với SMTP/Slack/Webhook đã cấu hình."""
    if ALERT_DISPATCH_ENABLED:
        return CompositeAlertDispatcher()
    # Dùng chung 1 instance in-memory trong tiến trình để test có thể
    # kiểm tra lại `sent_alerts` sau khi gọi API.
    return _inmemory_singleton