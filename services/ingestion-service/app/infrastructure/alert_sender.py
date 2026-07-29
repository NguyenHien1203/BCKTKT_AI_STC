"""Triển khai CredentialAlertSender (interface khai báo ở domain/repositories.py).

Khi tích hợp thật: thêm class `AlertmanagerAlertSender` (POST tới
Alertmanager API `/api/v2/alerts` theo ARCHITECTURE.md mục Observability —
Prometheus/Alertmanager) ở đây, rồi đổi factory ở
app/interfaces/api/credential_asset_router.py — không cần sửa
domain/application.
"""
from app.domain.repositories import CredentialAlertSender


class NoOpAlertmanagerAlertSender(CredentialAlertSender):
    """Dùng cho môi trường dev/test khi chưa nối Alertmanager thật.

    Coi là gửi cảnh báo thành công — chỉ log lại nội dung để tiện debug/test,
    không thực sự gọi Alertmanager thật.
    """

    def send_expiry_alert(
        self,
        asset_type: str,
        connection_id: int,
        expires_at: str,
        days_remaining: int,
    ) -> tuple:
        message = (
            f"[Alertmanager giả lập] {asset_type} của connection id={connection_id} "
            f"sẽ hết hạn vào {expires_at} (còn {days_remaining} ngày)"
        )
        print(f"[NoOpAlertmanagerAlertSender] {message}")
        return True, message