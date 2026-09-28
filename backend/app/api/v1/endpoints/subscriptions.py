import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories.subscription_repository import SqlAlchemySubscriptionRepository
from app.application.subscriptions.service import SubscriptionService
from app.application.subscriptions.dtos import (
    CreateSubscriptionDTO,
    UpdateSubscriptionDTO,
    PlanAlternativeDTO,
)
from app.domain.subscriptions.entities import SubscriptionStatus
from app.domain.subscriptions.exceptions import (
    SubscriptionNotFoundError,
    InvalidLifecycleTransitionError,
    InvalidMoneyError,
)
from app.api.v1.schemas.subscription import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionResponse,
    PaginatedSubscriptionResponse,
    PlanAlternativeSchema,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def get_subscription_service(session: AsyncSession = Depends(get_session)) -> SubscriptionService:
    repo = SqlAlchemySubscriptionRepository(session)
    return SubscriptionService(repo)


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    try:
        dto = CreateSubscriptionDTO(
            user_id=current_user.id,
            name=request.name,
            price=request.price,
            currency=request.currency,
            billing_cadence=request.billing_cadence,
            renewal_date=request.renewal_date,
            plan_alternatives=[
                PlanAlternativeDTO(
                    name=alt.name,
                    price=alt.price,
                    currency=alt.currency,
                    billing_cadence=alt.billing_cadence,
                    notes=alt.notes,
                )
                for alt in request.plan_alternatives
            ],
        )
        return await service.create_subscription(dto, current_user=current_user)
    except InvalidMoneyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=PaginatedSubscriptionResponse)
async def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[SubscriptionStatus] = Query(None),
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    skip = (page - 1) * page_size
    items, total = await service.list_subscriptions(
        current_user=current_user, skip=skip, limit=page_size, status=status
    )
    return PaginatedSubscriptionResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: uuid.UUID,
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    try:
        return await service.get_subscription(subscription_id, current_user=current_user)
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: uuid.UUID,
    request: SubscriptionUpdateRequest,
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    try:
        dto = UpdateSubscriptionDTO(
            name=request.name,
            price=request.price,
            currency=request.currency,
            billing_cadence=request.billing_cadence,
            renewal_date=request.renewal_date,
            status=request.status,
            plan_alternatives=[
                PlanAlternativeDTO(
                    name=alt.name,
                    price=alt.price,
                    currency=alt.currency,
                    billing_cadence=alt.billing_cadence,
                    notes=alt.notes,
                )
                for alt in request.plan_alternatives
            ] if request.plan_alternatives is not None else None,
        )
        return await service.update_subscription(subscription_id, dto, current_user=current_user)
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidLifecycleTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidMoneyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: uuid.UUID,
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    try:
        await service.delete_subscription(subscription_id, current_user=current_user)
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))