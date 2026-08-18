"""UC-065 — Cung cấp API qua LGSP.

Flow:
  (1) Cổng LGSP chuyển tiếp yêu cầu -> Hệ thống nhận.
  (2) Cổng API kiểm tra chứng thư mTLS -> Hệ thống thực thi.
  (3) Trả phản hồi theo chuẩn LGSP -> Hệ thống response.

`LgspGatewayService.handle_lgsp_request()` là điểm vào DUY NHẤT thực hiện
cả 3 bước theo đúng thứ tự. Khác với UC-064 (Data API cho IOC, dùng khoá
API xác thực và trả lỗi HTTP 401/403/429), tích hợp LGSP là kênh giao tiếp
HỆ THỐNG-VỚI-HỆ THỐNG (Cổng LGSP <-> Cổng API): xác thực dựa trên CHỨNG
THƯ mTLS (đã đăng ký/luân chuyển/thu hồi ở UC-062, tái dùng nguyên vẹn kho
tin cậy + CRL) do hạ tầng mTLS termination (vd Envoy/Nginx) trích xuất và
CHUYỂN TIẾP qua header `X-Client-Cert-Serial`; VÀ bước cuối luôn phải "trả
phản hồi theo chuẩn LGSP" — tức LUÔN đóng gói kết quả (thành công lẫn bị
từ chối/lỗi) vào 1 PHONG BÌ (envelope) JSON thống nhất `response_code` /
`response_message` thay vì trả lỗi HTTP rời rạc, nên mọi lỗi nghiệp vụ
(`LgspCertificateMissing`/`Invalid`/`Revoked`/`InvalidLgspRequest`/
`LgspRequestExecutionFailed`) được BẮT NỘI BỘ trong service này, KHÔNG để
lộ ra ngoài dưới dạng exception cho router.

Mọi lượt gọi (kể cả bị từ chối) đều được ghi vào `audit.audit_log`
(`api_type="LGSP"`, tái dùng nguyên vẹn bảng dùng chung của UC-064) để
Quản trị API tra cứu lại lịch sử tích hợp LGSP.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.domain.entities import AuditLogEntry
from app.domain.exceptions import (
    InvalidLgspRequest,
    LgspCertificateInvalid,
    LgspCertificateMissing,
    LgspCertificateRevoked,
    LgspRequestExecutionFailed,
)
from app.domain.repositories import (
    AuditLogRepository,
    CertificateRevocationEntryRepository,
    DataApiSemanticLayerClient,
    MtlsCertificateRepository,
)

API_TYPE = "LGSP"
ENDPOINT_PATH = "/lgsp/request"
RESPONSE_CODE_SUCCESS = "00"
RESPONSE_MESSAGE_SUCCESS = "Thành công"


def _now() -> datetime:
    # Dùng UTC "naive" (không kèm tzinfo) — nhất quán với cách các cột
    # `DateTime` (không `timezone=True`) của SQLAlchemy trong service này
    # lưu trữ (vd `not_before`/`not_after` của `MtlsCertificate`, UC-062),
    # tránh lỗi so sánh "can't compare offset-naive and offset-aware
    # datetimes" khi gọi `MtlsCertificate.is_valid_at(now)`.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LgspGatewayService:
    def __init__(
        self,
        mtls_certificate_repo: MtlsCertificateRepository,
        crl_repo: CertificateRevocationEntryRepository,
        audit_log_repo: AuditLogRepository,
        semantic_layer_client: DataApiSemanticLayerClient,
    ) -> None:
        self._mtls_repo = mtls_certificate_repo
        self._crl_repo = crl_repo
        self._audit_log_repo = audit_log_repo
        self._semantic_layer_client = semantic_layer_client

    # ------------------------------------------------------------------
    # Điểm vào chính — bước 1 (nhận) + bước 2 (kiểm tra mTLS + thực thi)
    # + bước 3 (đóng gói phản hồi chuẩn LGSP).
    # ------------------------------------------------------------------
    def handle_lgsp_request(
        self,
        client_cert_serial: Optional[str],
        request_id: str,
        service_code: str,
        payload: Dict[str, Any],
        consumer_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = _now()
        payload = payload or {}

        # Bước 1 — "Cổng LGSP chuyển tiếp yêu cầu -> Hệ thống nhận": xác
        # nhận yêu cầu hợp lệ tối thiểu trước khi kiểm tra chứng thư.
        try:
            self._validate_request(request_id, service_code)
        except InvalidLgspRequest as exc:
            return self._log_and_build_envelope(
                request_id=request_id,
                lgsp_code=exc.lgsp_code,
                message=str(exc),
                data=None,
                consumer_code="UNKNOWN",
                status="DENIED",
                service_code=service_code,
                payload=payload,
                consumer_ip=consumer_ip,
                when=now,
            )

        # Bước 2a — Cổng API kiểm tra chứng thư mTLS.
        try:
            consumer_code = self._verify_mtls_certificate(client_cert_serial, now)
        except (LgspCertificateMissing, LgspCertificateInvalid, LgspCertificateRevoked) as exc:
            return self._log_and_build_envelope(
                request_id=request_id,
                lgsp_code=exc.lgsp_code,
                message=str(exc),
                data=None,
                consumer_code=getattr(exc, "consumer_code", None) or "UNKNOWN",
                status="DENIED",
                service_code=service_code,
                payload=payload,
                consumer_ip=consumer_ip,
                when=now,
            )

        # Bước 2b — "Hệ thống thực thi": chứng thư hợp lệ -> gọi Lớp ngữ
        # nghĩa lấy dữ liệu tương ứng `service_code` (tái dùng đúng cổng
        # `DataApiSemanticLayerClient` của UC-064 — cùng bản chất "trả dữ
        # liệu tổng hợp" nhưng qua kênh LGSP thay vì khoá API IOC).
        try:
            rows = self._semantic_layer_client.query_aggregated_data(service_code, payload)
        except Exception as exc:  # noqa: BLE001 - bọc lại thành lỗi nghiệp vụ E05
            return self._log_and_build_envelope(
                request_id=request_id,
                lgsp_code=LgspRequestExecutionFailed(str(exc)).lgsp_code,
                message=str(exc) or "Hệ thống thực thi yêu cầu LGSP thất bại",
                data=None,
                consumer_code=consumer_code,
                status="ERROR",
                service_code=service_code,
                payload=payload,
                consumer_ip=consumer_ip,
                when=now,
            )

        # Bước 3 — "Trả phản hồi theo chuẩn LGSP -> Hệ thống response".
        data = {"service_code": service_code, "row_count": len(rows), "rows": rows}
        return self._log_and_build_envelope(
            request_id=request_id,
            lgsp_code=RESPONSE_CODE_SUCCESS,
            message=RESPONSE_MESSAGE_SUCCESS,
            data=data,
            consumer_code=consumer_code,
            status="SUCCESS",
            service_code=service_code,
            payload=payload,
            row_count=len(rows),
            consumer_ip=consumer_ip,
            when=now,
        )

    # ------------------------------------------------------------------
    # Bước 1 — validate tối thiểu yêu cầu LGSP chuyển tiếp.
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_request(request_id: str, service_code: str) -> None:
        if not request_id or not request_id.strip():
            raise InvalidLgspRequest("Mã giao dịch (request_id) không được để trống")
        if not service_code or not service_code.strip():
            raise InvalidLgspRequest("Mã dịch vụ (service_code) không được để trống")

    # ------------------------------------------------------------------
    # Bước 2a — Cổng API kiểm tra chứng thư mTLS (tái dùng kho tin cậy +
    # CRL của UC-062).
    # ------------------------------------------------------------------
    def _verify_mtls_certificate(self, client_cert_serial: Optional[str], now: datetime) -> str:
        if not client_cert_serial or not client_cert_serial.strip():
            raise LgspCertificateMissing()

        serial_number = client_cert_serial.strip()
        certificate = self._mtls_repo.get_by_serial_number(serial_number)
        if certificate is None:
            raise LgspCertificateInvalid(
                f"Không tìm thấy chứng thư mTLS số hiệu '{serial_number}' trong kho tin cậy"
            )

        crl_entry = self._crl_repo.get_by_serial_number(serial_number)
        if crl_entry is not None or certificate.status == "REVOKED":
            raise LgspCertificateRevoked(serial_number, consumer_code=certificate.consumer_code)

        if not certificate.is_valid_at(now):
            raise LgspCertificateInvalid(
                f"Chứng thư mTLS số hiệu '{serial_number}' không ở trạng thái ACTIVE "
                "hoặc đã hết/chưa tới thời hạn hiệu lực",
                consumer_code=certificate.consumer_code,
            )

        return certificate.consumer_code

    # ------------------------------------------------------------------
    # Bước 3 — Ghi `audit.audit_log` + dựng phong bì phản hồi chuẩn LGSP.
    # ------------------------------------------------------------------
    def _log_and_build_envelope(
        self,
        request_id: str,
        lgsp_code: str,
        message: str,
        data: Optional[Dict[str, Any]],
        consumer_code: str,
        status: str,
        service_code: str,
        payload: Dict[str, Any],
        when: datetime,
        row_count: Optional[int] = None,
        consumer_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_params = json.dumps(
            {"request_id": request_id, "service_code": service_code, "payload": payload},
            ensure_ascii=False,
        )
        self._audit_log_repo.add(
            AuditLogEntry(
                id=None,
                api_type=API_TYPE,
                endpoint_path=ENDPOINT_PATH,
                consumer_code=consumer_code,
                status=status,
                api_key_id=None,
                reason=message if status != "SUCCESS" else "",
                request_params=request_params,
                row_count=row_count,
                consumer_ip=consumer_ip,
                called_at=when,
            )
        )
        return {
            "request_id": request_id,
            "response_code": lgsp_code,
            "response_message": message,
            "processed_at": when,
            "data": data,
        }

    # ------------------------------------------------------------------
    # Tra cứu nhật ký (hỗ trợ Quản trị API xem lại lịch sử tích hợp LGSP).
    # ------------------------------------------------------------------
    def list_lgsp_logs(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ):
        return self._audit_log_repo.list(
            api_type=API_TYPE, consumer_code=consumer_code, status=status, limit=limit
        )