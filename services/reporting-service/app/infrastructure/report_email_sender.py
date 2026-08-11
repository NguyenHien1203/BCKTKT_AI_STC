"""Implementation của cổng `ReportEmailSender` — UC-051 bước cuối: "Hệ
thống tự động sinh + gửi email báo cáo theo lịch".

`SmtpReportEmailSender` gửi qua máy chủ SMTP cấu hình bằng biến môi
trường (giống mọi service khác trong hệ thống chỉ cấu hình qua env, xem
`.env.example`). `NoOpReportEmailSender` dùng cho dev/test khi chưa cấu
hình SMTP thật (`REPORT_SMTP_HOST` trống) — chỉ ghi lại (in-memory, dùng
để test) danh sách email "đã gửi", KHÔNG thay thế cho
`SmtpReportEmailSender` khi triển khai thật.
"""
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.domain.exceptions import ReportEmailSendFailed
from app.domain.repositories import ReportEmailSender


class ReportSmtpConfig:
    HOST: str = os.getenv("REPORT_SMTP_HOST", "")
    PORT: int = int(os.getenv("REPORT_SMTP_PORT", "587"))
    USERNAME: str = os.getenv("REPORT_SMTP_USERNAME", "")
    PASSWORD: str = os.getenv("REPORT_SMTP_PASSWORD", "")
    USE_TLS: bool = os.getenv("REPORT_SMTP_USE_TLS", "true").lower() == "true"
    FROM_ADDRESS: str = os.getenv("REPORT_SMTP_FROM", "bao-cao@stc.gov.vn")


class SmtpReportEmailSender(ReportEmailSender):
    def __init__(self, config: ReportSmtpConfig = ReportSmtpConfig):
        self._config = config

    def send_report_email(
        self,
        to_emails: List[str],
        subject: str,
        body_text: str,
        attachment_filename: str,
        attachment_bytes: bytes,
        attachment_mime_type: str,
    ) -> None:
        message = MIMEMultipart()
        message["From"] = self._config.FROM_ADDRESS
        message["To"] = ", ".join(to_emails)
        message["Subject"] = subject
        message.attach(MIMEText(body_text, "plain", "utf-8"))

        maintype, _, subtype = attachment_mime_type.partition("/")
        attachment = MIMEApplication(attachment_bytes, _subtype=subtype or "octet-stream")
        attachment.add_header(
            "Content-Disposition", "attachment", filename=attachment_filename
        )
        message.attach(attachment)

        try:
            with smtplib.SMTP(self._config.HOST, self._config.PORT, timeout=20) as server:
                if self._config.USE_TLS:
                    server.starttls()
                if self._config.USERNAME:
                    server.login(self._config.USERNAME, self._config.PASSWORD)
                server.sendmail(self._config.FROM_ADDRESS, to_emails, message.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            raise ReportEmailSendFailed(
                f"Không gửi được email báo cáo qua SMTP ({self._config.HOST}): {exc}"
            ) from exc


@dataclass
class _SentEmailRecord:
    to_emails: List[str]
    subject: str
    attachment_filename: str


class NoOpReportEmailSender(ReportEmailSender):
    """Dùng cho dev/test khi chưa cấu hình SMTP thật (`REPORT_SMTP_HOST`
    trống) — không gọi mạng, chỉ ghi lại (in-memory) để kiểm tra trong
    test, KHÔNG thay thế cho `SmtpReportEmailSender` khi triển khai thật.
    """

    sent_emails: List[_SentEmailRecord] = field(default_factory=list)

    def __init__(self):
        self.sent_emails: List[_SentEmailRecord] = []

    def send_report_email(
        self,
        to_emails: List[str],
        subject: str,
        body_text: str,
        attachment_filename: str,
        attachment_bytes: bytes,
        attachment_mime_type: str,
    ) -> None:
        if not to_emails:
            raise ReportEmailSendFailed("Danh sách người nhận rỗng")
        self.sent_emails.append(
            _SentEmailRecord(
                to_emails=list(to_emails),
                subject=subject,
                attachment_filename=attachment_filename,
            )
        )


_noop_singleton = NoOpReportEmailSender()


def get_report_email_sender() -> ReportEmailSender:
    if ReportSmtpConfig.HOST:
        return SmtpReportEmailSender()
    # Dùng chung 1 instance NoOp trong tiến trình để test có thể kiểm tra
    # lại `sent_emails` sau khi gọi API (giống cách `NoOp*` khác trong
    # service này được factory hoá theo biến môi trường).
    return _noop_singleton