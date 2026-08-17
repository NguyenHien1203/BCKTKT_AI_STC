"""UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác.

Prefix `/mtls-certificates`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_mtls_certificate import MtlsCertificateService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCertificateRevocationEntryRepository,
    SqlAlchemyMtlsCertificateRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CertificateRevocationCheckResponse,
    CertificateRevocationEntryResponse,
    MtlsCertificateRegister,
    MtlsCertificateResponse,
    MtlsCertificateRevokeRequest,
    MtlsCertificateRotateRequest,
    MtlsCertificateRotateResponse,
)

router = APIRouter(prefix="/mtls-certificates", tags=["UC-062 - Quản lý chứng thư / mTLS"])


def _service(db: Session = Depends(get_db)) -> MtlsCertificateService:
    return MtlsCertificateService(
        certificate_repo=SqlAlchemyMtlsCertificateRepository(db),
        crl_repo=SqlAlchemyCertificateRevocationEntryRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "MTLS_CERTIFICATE_NOT_FOUND": 404,
        "MTLS_CERTIFICATE_SERIAL_ALREADY_EXISTS": 409,
        "MTLS_CERTIFICATE_ALREADY_REVOKED": 409,
        "MTLS_CERTIFICATE_NOT_ACTIVE": 409,
        "INVALID_MTLS_CERTIFICATE": 422,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=MtlsCertificateResponse, status_code=201)
def register_certificate(
    payload: MtlsCertificateRegister,
    service: MtlsCertificateService = Depends(_service),
):
    """Bước 1 — Đăng ký chứng thư của đơn vị khai thác -> hệ thống lưu
    vào kho tin cậy."""
    try:
        return service.register_certificate(
            consumer_code=payload.consumer_code,
            consumer_name=payload.consumer_name,
            common_name=payload.common_name,
            serial_number=payload.serial_number,
            pem_certificate=payload.pem_certificate,
            not_before=payload.not_before,
            not_after=payload.not_after,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.get("", response_model=list[MtlsCertificateResponse])
def list_certificates(
    consumer_code: Optional[str] = None,
    status: Optional[str] = None,
    service: MtlsCertificateService = Depends(_service),
):
    return service.list_certificates(consumer_code=consumer_code, status=status)


@router.get("/crl", response_model=list[CertificateRevocationEntryResponse])
def get_crl(
    consumer_code: Optional[str] = None,
    service: MtlsCertificateService = Depends(_service),
):
    """Bước 3 — Xem CRL (Certificate Revocation List) hiện hành."""
    return service.get_crl(consumer_code=consumer_code)


@router.get("/crl/{serial_number}/check", response_model=CertificateRevocationCheckResponse)
def check_revoked(
    serial_number: str,
    service: MtlsCertificateService = Depends(_service),
):
    """Cổng API dùng để kiểm tra nhanh 1 chứng thư đã có trong CRL
    (đã bị thu hồi) hay chưa, theo `serial_number`."""
    return CertificateRevocationCheckResponse(
        serial_number=serial_number,
        is_revoked=service.is_revoked(serial_number),
    )


@router.get("/{certificate_id}", response_model=MtlsCertificateResponse)
def get_certificate(
    certificate_id: int,
    service: MtlsCertificateService = Depends(_service),
):
    try:
        return service.get(certificate_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@router.post("/{certificate_id}/rotate", response_model=MtlsCertificateRotateResponse)
def rotate_certificate(
    certificate_id: int,
    payload: MtlsCertificateRotateRequest,
    service: MtlsCertificateService = Depends(_service),
):
    """Bước 2 — Luân chuyển chứng thư -> hệ thống cập nhật."""
    try:
        old_certificate, new_certificate = service.rotate_certificate(
            certificate_id=certificate_id,
            common_name=payload.common_name,
            serial_number=payload.serial_number,
            pem_certificate=payload.pem_certificate,
            not_before=payload.not_before,
            not_after=payload.not_after,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc
    return MtlsCertificateRotateResponse(
        old_certificate=old_certificate,
        new_certificate=new_certificate,
    )


@router.post("/{certificate_id}/revoke", response_model=MtlsCertificateResponse)
def revoke_certificate(
    certificate_id: int,
    payload: MtlsCertificateRevokeRequest,
    service: MtlsCertificateService = Depends(_service),
):
    """Bước 3 — Thu hồi chứng thư -> hệ thống thêm vào CRL."""
    try:
        return service.revoke_certificate(certificate_id, reason=payload.reason)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc