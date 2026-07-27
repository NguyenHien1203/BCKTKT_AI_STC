from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_integration_config import IntegrationConfigService
from app.domain.exceptions import DomainError, IntegrationEndpointNotFound
from app.infrastructure.connection_checker import NoOpConnectionChecker
from app.infrastructure.db.repository_impl import SqlAlchemyIntegrationEndpointRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    IntegrationEndpointResponse,
    KeycloakConfigUpdate,
    LgspConfigUpdate,
)

router = APIRouter(prefix="/integration-config", tags=["UC-07 Quản lý cấu hình tích hợp"])


def get_service(db: Session = Depends(get_db)) -> IntegrationConfigService:
    # NoOpConnectionChecker: khi tích hợp thật, đổi sang HttpConnectionChecker
    # (xem app/infrastructure/connection_checker.py) — không cần sửa domain/application.
    return IntegrationConfigService(
        SqlAlchemyIntegrationEndpointRepository(db), NoOpConnectionChecker()
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, IntegrationEndpointNotFound) else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=List[IntegrationEndpointResponse])
def list_integration_endpoints(service: IntegrationConfigService = Depends(get_service)):
    return service.list_all()


@router.get("/keycloak", response_model=IntegrationEndpointResponse)
def get_keycloak_config(service: IntegrationConfigService = Depends(get_service)):
    try:
        return service.get("KEYCLOAK")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/keycloak", response_model=IntegrationEndpointResponse)
def configure_keycloak(
    payload: KeycloakConfigUpdate, service: IntegrationConfigService = Depends(get_service)
):
    try:
        return service.configure_keycloak(
            base_url=payload.base_url, realm=payload.realm, client_id=payload.client_id
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/keycloak/recheck", response_model=IntegrationEndpointResponse)
def recheck_keycloak(service: IntegrationConfigService = Depends(get_service)):
    try:
        return service.recheck("KEYCLOAK")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/lgsp", response_model=IntegrationEndpointResponse)
def get_lgsp_config(service: IntegrationConfigService = Depends(get_service)):
    try:
        return service.get("LGSP")
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/lgsp", response_model=IntegrationEndpointResponse)
def configure_lgsp(
    payload: LgspConfigUpdate, service: IntegrationConfigService = Depends(get_service)
):
    try:
        return service.configure_lgsp(base_url=payload.base_url, protocol=payload.protocol)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/lgsp/recheck", response_model=IntegrationEndpointResponse)
def recheck_lgsp(service: IntegrationConfigService = Depends(get_service)):
    try:
        return service.recheck("LGSP")
    except DomainError as exc:
        raise _domain_error_to_http(exc)