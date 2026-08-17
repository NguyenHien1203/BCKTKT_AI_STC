"""UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác.

Flow:
  (1) Đăng ký chứng thư của đơn vị khai thác -> hệ thống lưu vào kho tin
      cậy.
  (2) Luân chuyển chứng thư -> hệ thống cập nhật.
  (3) Thu hồi chứng thư -> hệ thống thêm vào CRL.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.domain.entities import CertificateRevocationEntry, MtlsCertificate
from app.domain.exceptions import (
    InvalidMtlsCertificate,
    MtlsCertificateAlreadyRevoked,
    MtlsCertificateNotActive,
    MtlsCertificateNotFound,
    MtlsCertificateSerialAlreadyExists,
)
from app.domain.repositories import (
    CertificateRevocationEntryRepository,
    MtlsCertificateRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MtlsCertificateService:
    def __init__(
        self,
        certificate_repo: MtlsCertificateRepository,
        crl_repo: CertificateRevocationEntryRepository,
    ) -> None:
        self._certificate_repo = certificate_repo
        self._crl_repo = crl_repo

    # ------------------------------------------------------------------
    # Bước 1 — Đăng ký chứng thư của đơn vị khai thác -> hệ thống lưu vào
    # kho tin cậy.
    # ------------------------------------------------------------------
    def register_certificate(
        self,
        consumer_code: str,
        consumer_name: str,
        common_name: str,
        serial_number: str,
        pem_certificate: str,
        not_before: datetime,
        not_after: datetime,
    ) -> MtlsCertificate:
        existing = self._certificate_repo.get_by_serial_number(serial_number)
        if existing is not None:
            raise MtlsCertificateSerialAlreadyExists(serial_number)

        try:
            certificate = MtlsCertificate.register(
                consumer_code=consumer_code,
                consumer_name=consumer_name,
                common_name=common_name,
                serial_number=serial_number,
                pem_certificate=pem_certificate,
                not_before=not_before,
                not_after=not_after,
                when=_now(),
            )
        except ValueError as exc:
            raise InvalidMtlsCertificate(str(exc)) from exc

        return self._certificate_repo.add(certificate)

    # ------------------------------------------------------------------
    # Bước 2 — Luân chuyển chứng thư -> hệ thống cập nhật.
    # ------------------------------------------------------------------
    def rotate_certificate(
        self,
        certificate_id: int,
        common_name: str,
        serial_number: str,
        pem_certificate: str,
        not_before: datetime,
        not_after: datetime,
    ) -> Tuple[MtlsCertificate, MtlsCertificate]:
        """Trả về (chứng_thư_cũ_đã_ROTATED, chứng_thư_mới)."""
        old_certificate = self._get_or_raise(certificate_id)

        existing = self._certificate_repo.get_by_serial_number(serial_number)
        if existing is not None:
            raise MtlsCertificateSerialAlreadyExists(serial_number)

        now = _now()
        try:
            new_certificate = MtlsCertificate.register(
                consumer_code=old_certificate.consumer_code,
                consumer_name=old_certificate.consumer_name,
                common_name=common_name,
                serial_number=serial_number,
                pem_certificate=pem_certificate,
                not_before=not_before,
                not_after=not_after,
                when=now,
                previous_certificate_id=old_certificate.id,
            )
        except ValueError as exc:
            raise InvalidMtlsCertificate(str(exc)) from exc
        saved_new_certificate = self._certificate_repo.add(new_certificate)

        try:
            old_certificate.mark_rotated(when=now, new_certificate_id=saved_new_certificate.id)
        except ValueError as exc:
            raise MtlsCertificateNotActive(certificate_id) from exc
        updated_old_certificate = self._certificate_repo.update(old_certificate)

        return updated_old_certificate, saved_new_certificate

    # ------------------------------------------------------------------
    # Bước 3 — Thu hồi chứng thư -> hệ thống thêm vào CRL.
    # ------------------------------------------------------------------
    def revoke_certificate(self, certificate_id: int, reason: str = "") -> MtlsCertificate:
        certificate = self._get_or_raise(certificate_id)
        now = _now()
        try:
            certificate.revoke(when=now, reason=reason)
        except ValueError as exc:
            raise MtlsCertificateAlreadyRevoked(certificate_id) from exc
        updated = self._certificate_repo.update(certificate)

        self._crl_repo.add(
            CertificateRevocationEntry(
                id=None,
                certificate_id=updated.id,
                consumer_code=updated.consumer_code,
                serial_number=updated.serial_number,
                fingerprint_sha256=updated.fingerprint_sha256,
                reason=reason or "",
                revoked_at=now,
            )
        )
        return updated

    # ------------------------------------------------------------------
    # Truy vấn
    # ------------------------------------------------------------------
    def get(self, certificate_id: int) -> MtlsCertificate:
        return self._get_or_raise(certificate_id)

    def list_certificates(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[MtlsCertificate]:
        return self._certificate_repo.list(consumer_code=consumer_code, status=status)

    def get_crl(self, consumer_code: Optional[str] = None) -> List[CertificateRevocationEntry]:
        """Bước 3 — Xem CRL (Certificate Revocation List) hiện hành."""
        return self._crl_repo.list(consumer_code=consumer_code)

    def is_revoked(self, serial_number: str) -> bool:
        """Cổng API dùng để kiểm tra nhanh 1 chứng thư đã bị thu hồi hay
        chưa (tra CRL theo `serial_number`) lúc xác thực mTLS runtime."""
        return self._crl_repo.get_by_serial_number(serial_number) is not None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_or_raise(self, certificate_id: int) -> MtlsCertificate:
        certificate = self._certificate_repo.get_by_id(certificate_id)
        if certificate is None:
            raise MtlsCertificateNotFound(certificate_id)
        return certificate