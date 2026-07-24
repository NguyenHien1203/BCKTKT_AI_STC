from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_org_unit import OrgUnitService
from app.domain.exceptions import DomainError, OrgUnitNotFound
from app.infrastructure.db.repository_impl import SqlAlchemyOrgUnitRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    OrgUnitCreate,
    OrgUnitRename,
    OrgUnitResponse,
)

router = APIRouter(prefix="/org-units", tags=["UC-01 Quản lý cơ cấu tổ chức"])


def get_service(db: Session = Depends(get_db)) -> OrgUnitService:
    return OrgUnitService(SqlAlchemyOrgUnitRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, OrgUnitNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=OrgUnitResponse, status_code=201)
def create_org_unit(payload: OrgUnitCreate, service: OrgUnitService = Depends(get_service)):
    try:
        org_unit = service.create(
            code=payload.code,
            name=payload.name,
            unit_type=payload.unit_type,
            parent_id=payload.parent_id,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return org_unit


@router.get("", response_model=List[OrgUnitResponse])
def list_org_units(
    only_active: bool = Query(False),
    service: OrgUnitService = Depends(get_service),
):
    return service.list_units(only_active=only_active)


@router.get("/{org_unit_id}", response_model=OrgUnitResponse)
def get_org_unit(org_unit_id: int, service: OrgUnitService = Depends(get_service)):
    try:
        return service.get(org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{org_unit_id}/rename", response_model=OrgUnitResponse)
def rename_org_unit(
    org_unit_id: int,
    payload: OrgUnitRename,
    service: OrgUnitService = Depends(get_service),
):
    try:
        return service.rename(org_unit_id, payload.name)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/{org_unit_id}/deactivate", response_model=OrgUnitResponse)
def deactivate_org_unit(org_unit_id: int, service: OrgUnitService = Depends(get_service)):
    try:
        return service.deactivate(org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/{org_unit_id}/activate", response_model=OrgUnitResponse)
def activate_org_unit(org_unit_id: int, service: OrgUnitService = Depends(get_service)):
    try:
        return service.activate(org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete("/{org_unit_id}", status_code=204, responses={409: {"model": ErrorResponse}})
def delete_org_unit(org_unit_id: int, service: OrgUnitService = Depends(get_service)):
    try:
        service.delete(org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
