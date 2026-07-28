"""Triển khai NotificationSender (interface khai báo ở domain/repositories.py).

Khi tích hợp thật: thêm class SmtpNotificationSender (gửi email thật qua
smtplib), TwilioSmsSender (gọi API SMS thật), SlackWebhookSender (POST tới
Slack incoming webhook) ở đây, rồi đổi factory ở
app/interfaces/api/notification_channel_router.py — không cần sửa
domain/application.
"""
from app.domain.repositories import NotificationSender, PasswordEmailSender


class NoOpNotificationSender(NotificationSender):
    """Dùng cho môi trường dev/test khi chưa nối SMTP/SMS/Webhook thật.

    Coi là gửi thành công nếu cấu hình + người nhận hợp lệ (đã được domain
    validate cấu hình trước khi tới đây) — không thực sự gửi ra ngoài.
    """

    def send_test(self, channel_type: str, config: dict, recipient: str) -> tuple:
        if channel_type in ("SMTP", "SMS") and not recipient:
            kind = "email" if channel_type == "SMTP" else "số điện thoại"
            return False, f"Thiếu {kind} người nhận để gửi thử"
        if channel_type == "SMTP":
            return True, f"Đã gửi email kiểm thử tới {recipient} (giả lập NoOp, chưa nối SMTP thật)"
        if channel_type == "SMS":
            return True, f"Đã gửi SMS kiểm thử tới {recipient} (giả lập NoOp, chưa nối cổng SMS thật)"
        return True, "Đã gửi tin nhắn kiểm thử tới Webhook (giả lập NoOp, chưa nối Webhook/Slack thật)"


class NoOpPasswordEmailSender(PasswordEmailSender):
    """Dùng cho môi trường dev/test khi chưa nối SMTP thật (UC-13).

    Không gửi email thật ra ngoài — chỉ log lại nội dung để tiện debug/test.
    Khi tích hợp thật: thêm `SmtpPasswordEmailSender` (dùng smtplib + cấu hình
    ở NotificationChannel SMTP của UC-08) rồi đổi factory ở
    app/interfaces/api/password_router.py — không cần sửa domain/application.
    """

    def send_reset_link(self, to_email: str, reset_link: str) -> None:
        print(f"[NoOpPasswordEmailSender] Gửi link reset mật khẩu tới {to_email}: {reset_link}")

    def send_temp_password(self, to_email: str, temp_password: str) -> None:
        print(
            f"[NoOpPasswordEmailSender] Gửi mật khẩu tạm tới {to_email}: {temp_password}"
        )