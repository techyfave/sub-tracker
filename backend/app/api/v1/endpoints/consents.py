from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.openapi_responses import (
    CONSENT_VALIDATION_ERROR_EXAMPLE,
    PROBLEM_401,
    problem_response,
    response_with_instance,
)
from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.schemas.consents import (
    ConsentCreateRequest,
    ConsentListResponse,
    ConsentResponse,
)
from app.application.consents.service import ConsentService
from app.infrastructure.database.repositories.consent_repository import (
    SqlAlchemyConsentRepository,
)
from app.infrastructure.database.session import get_session

router = APIRouter(prefix="/consents", tags=["Consents"])

CONSENT_ID_EXAMPLE = "00000000-0000-0000-0000-000000000001"

CONSENT_VALIDATION_RESPONSE = problem_response(
    "The consent request contains invalid data.",
    {
        **CONSENT_VALIDATION_ERROR_EXAMPLE,
        "instance": "/api/v1/consents",
    },
    instance="/api/v1/consents",
)

CONSENT_UUID_VALIDATION_RESPONSE = problem_response(
    "The consent identifier must be a valid UUID.",
    {
        "type": "https://api.subtracker.dev/problems/validation-error",
        "title": "Validation Error",
        "status": 422,
        "detail": "The request contains invalid data.",
        "instance": "/api/v1/consents/not-a-uuid",
        "errors": [
            {
                "location": ["path", "consent_id"],
                "message": ("Input should be a valid UUID, invalid character: found `n` at 1"),
                "type": "uuid_parsing",
            }
        ],
    },
    instance="/api/v1/consents/not-a-uuid",
)

CONSENT_FORBIDDEN_RESPONSE = problem_response(
    "The consent belongs to another user.",
    {
        "type": "about:blank",
        "title": "Forbidden",
        "status": 403,
        "detail": "You do not have access to this resource.",
        "instance": f"/api/v1/consents/{CONSENT_ID_EXAMPLE}",
    },
    instance=f"/api/v1/consents/{CONSENT_ID_EXAMPLE}",
)

CONSENT_NOT_FOUND_RESPONSE = problem_response(
    "The consent does not exist.",
    {
        "type": "about:blank",
        "title": "HTTP Error",
        "status": 404,
        "detail": "Consent not found.",
        "instance": f"/api/v1/consents/{CONSENT_ID_EXAMPLE}",
    },
    instance=f"/api/v1/consents/{CONSENT_ID_EXAMPLE}",
)


def get_consent_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentService:
    return ConsentService(SqlAlchemyConsentRepository(session))


@router.post(
    "",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: response_with_instance(PROBLEM_401, "/api/v1/consents"),
        422: CONSENT_VALIDATION_RESPONSE,
    },
)
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


@router.get(
    "",
    response_model=ConsentListResponse,
    responses={
        401: response_with_instance(PROBLEM_401, "/api/v1/consents"),
    },
)
async def list_consents(
    current_user: CurrentUser,
    service: Annotated[ConsentService, Depends(get_consent_service)],
) -> ConsentListResponse:
    items = await service.list_for_user(user_id=current_user.id)
    return ConsentListResponse(items=[ConsentResponse.model_validate(item) for item in items])


@router.delete(
    "/{consent_id}",
    response_model=ConsentResponse,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            f"/api/v1/consents/{CONSENT_ID_EXAMPLE}",
        ),
        403: CONSENT_FORBIDDEN_RESPONSE,
        404: CONSENT_NOT_FOUND_RESPONSE,
        422: CONSENT_UUID_VALIDATION_RESPONSE,
    },
)
async def revoke_consent(
    consent_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ConsentService, Depends(get_consent_service)],
) -> ConsentResponse:
    consent = await service.revoke(
        consent_id=consent_id,
        user_id=current_user.id,
    )
    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found.",
        )

    return ConsentResponse.model_validate(consent)
