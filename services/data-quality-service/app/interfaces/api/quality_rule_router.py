from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_quality_rule import QualityRuleService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyQualityRuleRepository,
    SqlAlchemyQualityRuleVersionRepository,
    SqlAlchemyQualityScoreConfigRepository,
    SqlAlchemyQualityScoreConfigVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    QualityRuleCreate,
    QualityRuleResponse,
    QualityRuleUpdate,
    QualityRuleVersionResponse,
    QualityScoreConfigResponse,
    QualityScoreConfigSave,
    QualityScoreConfigVersionResponse,
)

router = APIRouter(prefix="/quality-rules", tags=["UC-038 Quản lý quy tắc kiểm tra chất lượng"])


def get_service(db: Session = Depends(get_db)) -> QualityRuleService:
    return QualityRuleService(
        rule_repo=SqlAlchemyQualityRuleRepository(db),
        rule_version_repo=SqlAlchemyQualityRuleVersionRepository(db),
        score_config_repo=SqlAlchemyQualityScoreConfigRepository(db),
        score_config_version_repo=SqlAlchemyQualityScoreConfigVersionRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem danh sách quy tắc chất lượng ----------


@router.get("", response_model=List[QualityRuleResponse])
def list_quality_rules(
    dataset_id: Optional[int] = Query(
        None, description="Lọc theo tập dữ liệu -- bỏ trống để xem cả quy tắc chung"
    ),
    rule_type: Optional[str] = Query(
        None, description="COMPLETENESS (đầy đủ) / VALIDITY (hợp lệ) / UNIQUENESS (duy nhất) / CONSISTENCY (nhất quán)"
    ),
    is_active: Optional[bool] = Query(None),
    service: QualityRuleService = Depends(get_service),
):
    """Bước 1 'Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ / duy

    nhất / nhất quán)' -- hệ thống hiển thị."""
    rules = service.list_rules(dataset_id=dataset_id, rule_type=rule_type, is_active=is_active)
    return [QualityRuleResponse.from_entity(r) for r in rules]


@router.get(
    "/{rule_id}",
    response_model=QualityRuleResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_quality_rule(rule_id: int, service: QualityRuleService = Depends(get_service)):
    try:
        return QualityRuleResponse.from_entity(service.get(rule_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{rule_id}/versions",
    response_model=List[QualityRuleVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_quality_rule_versions(rule_id: int, service: QualityRuleService = Depends(get_service)):
    try:
        versions = service.list_versions(rule_id)
        return [QualityRuleVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Thêm / Sửa quy tắc ----------


@router.post(
    "",
    response_model=QualityRuleResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
)
def create_quality_rule(
    payload: QualityRuleCreate, service: QualityRuleService = Depends(get_service)
):
    """Bước 2 'Thêm quy tắc' -- hệ thống lưu vào `metadata.quality_rules`

    + version."""
    try:
        rule = service.create_rule(
            field_names=payload.field_names,
            rule_type=payload.rule_type,
            dataset_id=payload.dataset_id,
            params=payload.params,
            weight=payload.weight,
            description=payload.description,
            is_active=payload.is_active,
            note=payload.note,
        )
        return QualityRuleResponse.from_entity(rule)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{rule_id}",
    response_model=QualityRuleResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_quality_rule(
    rule_id: int, payload: QualityRuleUpdate, service: QualityRuleService = Depends(get_service)
):
    """Bước 2 'Sửa quy tắc' -- hệ thống lưu vào `metadata.quality_rules`

    + version (tăng version + ghi lịch sử)."""
    try:
        rule = service.update_rule(
            rule_id,
            field_names=payload.field_names,
            params=payload.params,
            weight=payload.weight,
            description=payload.description,
            is_active=payload.is_active,
            note=payload.note,
        )
        return QualityRuleResponse.from_entity(rule)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Cấu hình ngưỡng + trọng số cho điểm ----------


@router.get("/score-configs/list", response_model=List[QualityScoreConfigResponse])
def list_quality_score_configs(service: QualityRuleService = Depends(get_service)):
    return [QualityScoreConfigResponse.from_entity(c) for c in service.list_score_configs()]


@router.get(
    "/score-configs/by-dataset",
    response_model=QualityScoreConfigResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_quality_score_config_by_dataset(
    dataset_id: Optional[int] = Query(
        None, description="Bỏ trống để lấy cấu hình MẶC ĐỊNH (dataset_id=null)"
    ),
    service: QualityRuleService = Depends(get_service),
):
    try:
        return QualityScoreConfigResponse.from_entity(service.get_score_config(dataset_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/score-configs/{config_id}",
    response_model=QualityScoreConfigResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_quality_score_config(config_id: int, service: QualityRuleService = Depends(get_service)):
    try:
        return QualityScoreConfigResponse.from_entity(service.get_score_config_by_id(config_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/score-configs/{config_id}/versions",
    response_model=List[QualityScoreConfigVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_quality_score_config_versions(
    config_id: int, service: QualityRuleService = Depends(get_service)
):
    try:
        versions = service.list_score_config_versions(config_id)
        return [QualityScoreConfigVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/score-configs",
    response_model=QualityScoreConfigResponse,
    responses={422: {"model": ErrorResponse}},
)
def save_quality_score_config(
    payload: QualityScoreConfigSave, service: QualityRuleService = Depends(get_service)
):
    """Bước 3 'Cấu hình ngưỡng + trọng số cho điểm' -- hệ thống lưu.

    Tạo mới cấu hình nếu `dataset_id` chưa có, ngược lại cập nhật
    (tăng version + ghi lịch sử)."""
    try:
        config = service.save_score_config(
            pass_threshold=payload.pass_threshold,
            dataset_id=payload.dataset_id,
            rule_type_weights=payload.rule_type_weights,
            note=payload.note,
        )
        return QualityScoreConfigResponse.from_entity(config)
    except DomainError as exc:
        raise _domain_error_to_http(exc)