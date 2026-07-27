from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_notification_channel import NotificationChannelService
from app.domain.exceptions import DomainError, NotificationChannelNotFound
from app.infrastructure.db.repository_impl import SqlAlchemyNotificationChannelRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.notification_sender import NoOpNotificationSender
from app.interfaces.api.schemas import (
    NotificationChannelResponse,
    SendTestRequest,
    SmsConfigUpdate,
    SmtpConfigUpdate,
    WebhookConfigUpdate,
)

router = APIRouter(prefix="/notification-channels", tags=["UC-08 Quản lý cấu hình kênh thông báo"])


def get_service(db: Session = Depends(get_db)) -> NotificationChannelService:
    # NoOpNotificationSender: khi tích hợp thật, đổi sang SmtpNotificationSender /
    # TwilioSmsSender / SlackWebhookSender tương ứng (xem
    # app/infrastructure/notification_sender.py) — không cần sửa domain/application.
    return NotificationChannelService(
        SqlAlchemyNotificationChannelRepository(db), NoOpNotificationSender()
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, NotificationChannelNotFound) else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=List[NotificationChannelResponse])
def list_notification_channels(service: NotificationChannelService = Depends(get_service)):
    return service.list_all()


@router.get("/smtp", response_model=NotificationChannelResponse)
def get_smtp_config(service: NotificationChannelService = Depends(get_service)):
    try:
        return service.get("SMTP")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/smtp", response_model=NotificationChannelResponse)
def configure_smtp(
    payload: SmtpConfigUpdate, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.configure_smtp(
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            from_email=payload.from_email,
            username=payload.username,
            password=payload.password,
            test_recipient=payload.test_recipient,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/smtp/test", response_model=NotificationChannelResponse)
def send_smtp_test(
    payload: SendTestRequest, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.send_test("SMTP", payload.recipient)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/sms", response_model=NotificationChannelResponse)
def get_sms_config(service: NotificationChannelService = Depends(get_service)):
    try:
        return service.get("SMS")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/sms", response_model=NotificationChannelResponse)
def configure_sms(
    payload: SmsConfigUpdate, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.configure_sms(
            gateway_url=payload.gateway_url,
            api_key=payload.api_key,
            test_recipient=payload.test_recipient,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/sms/test", response_model=NotificationChannelResponse)
def send_sms_test(
    payload: SendTestRequest, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.send_test("SMS", payload.recipient)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/webhook", response_model=NotificationChannelResponse)
def get_webhook_config(service: NotificationChannelService = Depends(get_service)):
    try:
        return service.get("WEBHOOK")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/webhook", response_model=NotificationChannelResponse)
def configure_webhook(
    payload: WebhookConfigUpdate, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.configure_webhook(webhook_url=payload.webhook_url)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/webhook/test", response_model=NotificationChannelResponse)
def send_webhook_test(
    payload: SendTestRequest, service: NotificationChannelService = Depends(get_service)
):
    try:
        return service.send_test("WEBHOOK", payload.recipient)
    except DomainError as exc:
        raise _domain_error_to_http(exc)