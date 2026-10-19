from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.schemas.consents import ConsentCreateRequest, ConsentListResponse, ConsentResponse
from app.application.consents.service import ConsentService
from app.infrastructure.database.repositories.consent_repository import SqlAlchemyConsentRepository
from app.infrastructure.database.session import get_session

router = APIRouter(prefix="/consents", tags=["Consents"])


def get_consent_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ConsentService:
    return ConsentService(SqlAlchemyConsentRepository(session))


@router.post("", status_code=status.HTTP_201_CREATED)
async def grant_consent(
    request: ConsentCreateRequest,
    current_user: CurrentUser,
    service: Annotated[ConsentService, Depends(get_consent_service)],
) -> ConsentResponse:
    consent = await service.grant(
        user_id=current_user.id,
        policy_version=request.policy_version,
        scopes=request.scopes,
    )
    return ConsentResponse.model_validate(consent)


@router.get("")
async def list_consents(
    current_user: CurrentUser,
    service: Annotated[ConsentService, Depends(get_consent_service)],
) -> ConsentListResponse:
    items = await service.list_for_user(user_id=current_user.id)
    return ConsentListResponse(items=[ConsentResponse.model_validate(item) for item in items])


@router.delete("/{consent_id}")
async def revoke_consent(
    consent_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ConsentService, Depends(get_consent_service)],
) -> ConsentResponse:
    consent = await service.revoke(consent_id=consent_id, user_id=current_user.id)
    if consent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found.")
    return ConsentResponse.model_validate(consent)
