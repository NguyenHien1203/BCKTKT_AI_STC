from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_mapping_rule import MappingRuleService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import SqlAlchemyMappingRuleRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import ErrorResponse, MappingRuleCreate, MappingRuleResponse

router = APIRouter(prefix="/mapping-rules", tags=["UC-031 Ánh xạ trường sang dạng chuẩn"])


def get_service(db: Session = Depends(get_db)) -> MappingRuleService:
    return MappingRuleService(rule_repo=SqlAlchemyMappingRuleRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "",
    response_model=MappingRuleResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
)
def create_mapping_rule(
    payload: MappingRuleCreate,
    service: MappingRuleService = Depends(get_service),
):
    """Đăng ký 1 quy tắc ánh xạ (`metadata.mapping_rules`) -- dữ liệu đầu
    vào bắt buộc cho bước 1 của UC-031."""
    try:
        rule = service.create_rule(
            field_name=payload.field_name,
            version=payload.version,
            rule_type=payload.rule_type,
            dataset_id=payload.dataset_id,
            catalog_map=payload.catalog_map,
            normalize_case=payload.normalize_case,
            is_active=payload.is_active,
        )
        return MappingRuleResponse.from_entity(rule)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[MappingRuleResponse])
def list_mapping_rules(
    dataset_id: Optional[int] = Query(None),
    field_name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    service: MappingRuleService = Depends(get_service),
):
    rules = service.list_rules(dataset_id=dataset_id, field_name=field_name, is_active=is_active)
    return [MappingRuleResponse.from_entity(r) for r in rules]