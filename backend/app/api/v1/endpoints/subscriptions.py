import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.subscription import (
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.application.subscriptions.dtos import (
    CreateSubscriptionDTO,
    SubscriptionResponseDTO,
    UpdateSubscriptionDTO,
)
from app.application.subscriptions.service import SubscriptionService
from app.domain.subscriptions.entities import SubscriptionStatus
from app.domain.subscriptions.exceptions import (
    InvalidLifecycleTransitionError,
    SubscriptionNotFoundError,
)
from app.infrastructure.database.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.infrastructure.database.session import get_session

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)


def get_subscription_service(
    session: AsyncSession = Depends(get_session),
) -> SubscriptionService:
    repository = SqlAlchemySubscriptionRepository(session)
    return SubscriptionService(repository)


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponseDTO:
    dto = CreateSubscriptionDTO(
        user_id=current_user.id,
        plan_id=request.plan_id,
        name=request.name,
        status=request.status,
        provider_connection_id=request.provider_connection_id,
        started_at=request.started_at,
        renewal_at=request.renewal_at,
        ended_at=request.ended_at,
    )

    return await service.create_subscription(
        dto,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=SubscriptionListResponse,
)
async def list_subscriptions(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: SubscriptionStatus | None = Query(None),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionListResponse:
    skip = (page - 1) * page_size

    items, total = await service.list_subscriptions(
        current_user=current_user,
        skip=skip,
        limit=page_size,
        status=status,
    )

    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(item.__dict__) for item in items],
        pagination=PaginationMeta.create(
            page=page,
            page_size=page_size,
            total_items=total,
        ),
    )


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
)
async def get_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponseDTO:
    try:
        return await service.get_subscription(
            subscription_id,
            current_user=current_user,
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
)
async def update_subscription(
    subscription_id: uuid.UUID,
    request: SubscriptionUpdateRequest,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponseDTO:
    dto = UpdateSubscriptionDTO(
        plan_id=request.plan_id,
        provider_connection_id=request.provider_connection_id,
        name=request.name,
        status=request.status,
        started_at=request.started_at,
        renewal_at=request.renewal_at,
        ended_at=request.ended_at,
    )

    try:
        return await service.update_subscription(
            subscription_id,
            dto,
            current_user=current_user,
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidLifecycleTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> None:
    try:
        await service.delete_subscription(
            subscription_id,
            current_user=current_user,
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
