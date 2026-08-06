from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_semantic_indicator import SemanticIndicatorService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyIndicatorAuditLogRepository,
    SqlAlchemyIndicatorTestRunRepository,
    SqlAlchemySemanticIndicatorRepository,
    SqlAlchemySemanticIndicatorVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    IndicatorAuditLogResponse,
    IndicatorTestRequest,
    IndicatorTestRunResponse,
    SemanticIndicatorCreate,
    SemanticIndicatorResponse,
    SemanticIndicatorUpdate,
    SemanticIndicatorVersionResponse,
)

router = APIRouter(
    prefix="/semantic-indicators", tags=["UC-043 Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa"]
)


def get_service(db: Session = Depends(get_db)) -> SemanticIndicatorService:
    return SemanticIndicatorService(
        indicator_repo=SqlAlchemySemanticIndicatorRepository(db),
        version_repo=SqlAlchemySemanticIndicatorVersionRepository(db),
        test_run_repo=SqlAlchemyIndicatorTestRunRepository(db),
        audit_log_repo=SqlAlchemyIndicatorAuditLogRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "EXISTS" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Tạo chỉ tiêu mới ----------


@router.post(
    "",
    response_model=SemanticIndicatorResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_semantic_indicator(
    payload: SemanticIndicatorCreate, service: SemanticIndicatorService = Depends(get_service)
):
    """Bước 1 'Tạo chỉ tiêu mới (tên, mô tả, biểu thức, lĩnh vực)' --

    hệ thống lưu vào PostgreSQL."""
    try:
        indicator = service.create_indicator(
            name=payload.name,
            expression=payload.expression,
            domain=payload.domain,
            description=payload.description,
            created_by=payload.created_by,
            note=payload.note,
        )
        return SemanticIndicatorResponse.from_entity(indicator)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Quản lý phiên bản chỉ tiêu (sửa) ----------


@router.put(
    "/{indicator_id}",
    response_model=SemanticIndicatorResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_semantic_indicator(
    indicator_id: int,
    payload: SemanticIndicatorUpdate,
    service: SemanticIndicatorService = Depends(get_service),
):
    """Bước 3 'Quản lý phiên bản chỉ tiêu' -- hệ thống lưu version + audit."""
    description = "__unset__"
    if payload.clear_description:
        description = None
    elif payload.description is not None:
        description = payload.description
    try:
        indicator = service.update_indicator(
            indicator_id,
            name=payload.name,
            description=description,
            expression=payload.expression,
            domain=payload.domain,
            status=payload.status,
            changed_by=payload.changed_by,
            note=payload.note,
        )
        return SemanticIndicatorResponse.from_entity(indicator)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Kiểm thử chỉ tiêu trên truy vấn mẫu ----------


@router.post(
    "/{indicator_id}/test",
    response_model=IndicatorTestRunResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def test_semantic_indicator(
    indicator_id: int,
    payload: IndicatorTestRequest,
    service: SemanticIndicatorService = Depends(get_service),
):
    """Bước 2 'Kiểm thử chỉ tiêu trên truy vấn mẫu' -- hệ thống chạy và

    hiển thị kết quả (kể cả khi biểu thức lỗi lúc chạy, trả về
    `status=FAILED`+`error_message` thay vì lỗi HTTP)."""
    try:
        test_run = service.test_indicator(
            indicator_id, sample_rows=payload.sample_rows, tested_by=payload.tested_by
        )
        return IndicatorTestRunResponse.from_entity(test_run)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{indicator_id}/test-runs",
    response_model=List[IndicatorTestRunResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_indicator_test_runs(
    indicator_id: int, service: SemanticIndicatorService = Depends(get_service)
):
    try:
        runs = service.list_test_runs(indicator_id)
        return [IndicatorTestRunResponse.from_entity(r) for r in runs]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/test-runs/{test_run_id}",
    response_model=IndicatorTestRunResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_indicator_test_run(
    test_run_id: int, service: SemanticIndicatorService = Depends(get_service)
):
    try:
        return IndicatorTestRunResponse.from_entity(service.get_test_run(test_run_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Tra cứu ----------


@router.get("", response_model=List[SemanticIndicatorResponse])
def list_semantic_indicators(
    domain: Optional[str] = Query(None, description="Lọc theo lĩnh vực"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: DRAFT/ACTIVE/INACTIVE"),
    service: SemanticIndicatorService = Depends(get_service),
):
    items = service.list_indicators(domain=domain, status=status)
    return [SemanticIndicatorResponse.from_entity(i) for i in items]


@router.get(
    "/{indicator_id}",
    response_model=SemanticIndicatorResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_semantic_indicator(
    indicator_id: int, service: SemanticIndicatorService = Depends(get_service)
):
    try:
        return SemanticIndicatorResponse.from_entity(service.get_indicator(indicator_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{indicator_id}/versions",
    response_model=List[SemanticIndicatorVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_semantic_indicator_versions(
    indicator_id: int, service: SemanticIndicatorService = Depends(get_service)
):
    try:
        versions = service.list_versions(indicator_id)
        return [SemanticIndicatorVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{indicator_id}/audit-logs",
    response_model=List[IndicatorAuditLogResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_semantic_indicator_audit_logs(
    indicator_id: int, service: SemanticIndicatorService = Depends(get_service)
):
    try:
        logs = service.list_audit_logs(indicator_id)
        return [IndicatorAuditLogResponse.from_entity(a) for a in logs]
    except DomainError as exc:
        raise _domain_error_to_http(exc)