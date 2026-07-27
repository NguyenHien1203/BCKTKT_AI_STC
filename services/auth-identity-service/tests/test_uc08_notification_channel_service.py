"""Unit test cho UC-08 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_notification_channel import NotificationChannelService
from app.domain.entities import NotificationChannel
from app.domain.exceptions import InvalidNotificationChannel, NotificationChannelNotFound
from app.domain.repositories import NotificationChannelRepository, NotificationSender


class FakeNotificationChannelRepository(NotificationChannelRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def get_by_type(self, channel_type):
        for c in self._data.values():
            if c.channel_type == channel_type:
                return c
        return None

    def list(self):
        return list(self._data.values())

    def save(self, channel: NotificationChannel) -> NotificationChannel:
        if channel.id is None:
            channel.id = self._next_id
            self._next_id += 1
        self._data[channel.id] = channel
        return channel


class FakeNotificationSender(NotificationSender):
    """Fake có thể ép kết quả thành công/thất bại để test cả 2 nhánh."""

    def __init__(self, force_success: bool = True):
        self.force_success = force_success
        self.calls = []

    def send_test(self, channel_type, config, recipient):
        self.calls.append((channel_type, dict(config), recipient))
        if not self.force_success:
            return False, "Không thể gửi (giả lập lỗi)"
        if channel_type in ("SMTP", "SMS") and not recipient:
            return False, "Thiếu người nhận"
        return True, "OK"


@pytest.fixture
def repo():
    return FakeNotificationChannelRepository()


@pytest.fixture
def sender():
    return FakeNotificationSender(force_success=True)


@pytest.fixture
def service(repo, sender):
    return NotificationChannelService(repo, sender)


def test_configure_smtp_happy_path(service):
    channel = service.configure_smtp(
        smtp_host="smtp.hungyen.gov.vn",
        smtp_port=587,
        from_email="noreply@hungyen.gov.vn",
        username="noreply",
        password="secret",
    )
    assert channel.id == 1
    assert channel.channel_type == "SMTP"
    assert channel.config["smtp_host"] == "smtp.hungyen.gov.vn"
    assert channel.config["smtp_port"] == 587
    assert channel.is_verified is True
    assert channel.last_test_at is not None


def test_configure_smtp_defaults_test_recipient_to_from_email(service, sender):
    service.configure_smtp(
        smtp_host="smtp.hungyen.gov.vn", smtp_port=587, from_email="noreply@hungyen.gov.vn"
    )
    assert sender.calls[-1][2] == "noreply@hungyen.gov.vn"


def test_configure_smtp_invalid_port_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_smtp(smtp_host="smtp.x", smtp_port=99999, from_email="a@b.com")


def test_configure_smtp_invalid_email_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_smtp(smtp_host="smtp.x", smtp_port=587, from_email="not-an-email")


def test_configure_smtp_empty_host_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_smtp(smtp_host="  ", smtp_port=587, from_email="a@b.com")


def test_configure_sms_happy_path(service):
    channel = service.configure_sms(
        gateway_url="https://sms.hungyen.gov.vn", api_key="key123", test_recipient="0912345678"
    )
    assert channel.channel_type == "SMS"
    assert channel.config == {"gateway_url": "https://sms.hungyen.gov.vn", "api_key": "key123"}
    assert channel.is_verified is True


def test_configure_sms_invalid_gateway_url_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_sms(gateway_url="ftp://bad", api_key="key123", test_recipient="0912345678")


def test_configure_sms_missing_api_key_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_sms(
            gateway_url="https://sms.hungyen.gov.vn", api_key="", test_recipient="0912345678"
        )


def test_configure_webhook_happy_path(service):
    channel = service.configure_webhook(webhook_url="https://hooks.slack.com/services/xyz")
    assert channel.channel_type == "WEBHOOK"
    assert channel.config == {"webhook_url": "https://hooks.slack.com/services/xyz"}
    assert channel.is_verified is True


def test_configure_webhook_invalid_url_raises(service):
    with pytest.raises(InvalidNotificationChannel):
        service.configure_webhook(webhook_url="not-a-url")


def test_configure_reconfigure_resets_then_resends_test(service):
    service.configure_webhook(webhook_url="https://a.example/hook")
    updated = service.configure_webhook(webhook_url="https://b.example/hook")
    assert updated.config["webhook_url"] == "https://b.example/hook"
    assert updated.is_verified is True


def test_send_test_without_config_raises_not_found(service):
    with pytest.raises(NotificationChannelNotFound):
        service.send_test("SMTP")


def test_send_test_after_configure_updates_last_test_at(service):
    first = service.configure_webhook(webhook_url="https://a.example/hook")
    second = service.send_test("WEBHOOK")
    assert second.id == first.id
    assert second.is_verified is True


def test_get_without_config_raises_not_found(service):
    with pytest.raises(NotificationChannelNotFound):
        service.get("SMS")


def test_list_all_returns_configured_channels(service):
    service.configure_smtp(smtp_host="smtp.x", smtp_port=587, from_email="a@b.com")
    service.configure_webhook(webhook_url="https://a.example/hook")
    channels = service.list_all()
    types = {c.channel_type for c in channels}
    assert types == {"SMTP", "WEBHOOK"}


def test_send_failure_is_recorded_not_raised():
    repo = FakeNotificationChannelRepository()
    sender = FakeNotificationSender(force_success=False)
    service = NotificationChannelService(repo, sender)

    channel = service.configure_webhook(webhook_url="https://unreachable.example/hook")
    assert channel.is_verified is False
    assert channel.last_test_message == "Không thể gửi (giả lập lỗi)"


def test_sms_test_recipient_is_required_at_router_layer_but_service_still_records_failure_if_blank():
    repo = FakeNotificationChannelRepository()
    sender = FakeNotificationSender(force_success=True)
    service = NotificationChannelService(repo, sender)
    channel = service.configure_sms(gateway_url="https://sms.x", api_key="k", test_recipient="")
    assert channel.is_verified is False