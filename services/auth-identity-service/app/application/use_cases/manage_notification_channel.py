"""Application layer — UC-08: Quản lý cấu hình kênh thông báo.

Đối chiếu docs/use_cases.json id=8: cấu hình máy chủ SMTP (lưu + gửi email
kiểm thử), cấu hình cổng SMS (lưu + gửi SMS kiểm thử), cấu hình Webhook/Slack
(lưu + gửi tin nhắn kiểm thử). Việc lưu luôn thành công nếu dữ liệu hợp lệ;
gửi thử là bước tiếp theo, kết quả (thành công/thất bại) được ghi nhận lại
trên chính bản ghi để admin biết trạng thái hiện tại, không chặn việc lưu
cấu hình.
"""
from datetime import datetime, timezone

from app.domain.entities import NotificationChannel
from app.domain.exceptions import InvalidNotificationChannel, NotificationChannelNotFound
from app.domain.repositories import NotificationChannelRepository, NotificationSender


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationChannelService:
    def __init__(self, channel_repo: NotificationChannelRepository, sender: NotificationSender):
        self._channels = channel_repo
        self._sender = sender

    def _get_or_create(self, channel_type: str) -> NotificationChannel:
        channel = self._channels.get_by_type(channel_type)
        if channel is None:
            channel = NotificationChannel(id=None, channel_type=channel_type, config={})
        return channel

    def _configure(self, channel_type: str, config: dict, test_recipient: str) -> NotificationChannel:
        channel = self._get_or_create(channel_type)
        try:
            channel.configure(config)
        except ValueError as exc:
            raise InvalidNotificationChannel(str(exc)) from exc
        saved = self._channels.save(channel)
        return self._send_and_save(saved, test_recipient)

    def configure_smtp(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        username: str = "",
        password: str = "",
        test_recipient: str = "",
    ) -> NotificationChannel:
        """Cấu hình máy chủ SMTP — lưu + tự động gửi email kiểm thử."""
        return self._configure(
            "SMTP",
            {
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "from_email": from_email,
                "username": username,
                "password": password,
            },
            # Không có địa chỉ nhận riêng -> gửi thử về chính from_email.
            test_recipient or from_email,
        )

    def configure_sms(self, gateway_url: str, api_key: str, test_recipient: str) -> NotificationChannel:
        """Cấu hình cổng SMS — lưu + tự động gửi SMS kiểm thử tới `test_recipient`."""
        return self._configure(
            "SMS", {"gateway_url": gateway_url, "api_key": api_key}, test_recipient
        )

    def configure_webhook(self, webhook_url: str) -> NotificationChannel:
        """Cấu hình Webhook/Slack — lưu + tự động gửi tin nhắn kiểm thử."""
        return self._configure("WEBHOOK", {"webhook_url": webhook_url}, "")

    def _send_and_save(self, channel: NotificationChannel, recipient: str) -> NotificationChannel:
        is_verified, message = self._sender.send_test(channel.channel_type, channel.config, recipient)
        channel.record_test_result(is_verified, message, _utc_now_iso())
        return self._channels.save(channel)

    def send_test(self, channel_type: str, recipient: str = "") -> NotificationChannel:
        """Gửi lại thông điệp kiểm thử cho kênh đã cấu hình (không đổi cấu hình)."""
        channel = self._channels.get_by_type(channel_type)
        if channel is None:
            raise NotificationChannelNotFound(channel_type)
        return self._send_and_save(channel, recipient)

    def get(self, channel_type: str) -> NotificationChannel:
        channel = self._channels.get_by_type(channel_type)
        if channel is None:
            raise NotificationChannelNotFound(channel_type)
        return channel

    def list_all(self) -> list:
        return self._channels.list()