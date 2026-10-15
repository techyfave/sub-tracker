import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.subscription import (
    PlanInput,
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.api.v1.schemas.subscriptions import (
    TransactionCreate,
    UsageEventCreate,
)
from app.application.subscriptions.dtos import (
    CreateSubscriptionDTO,
    UpdateSubscriptionDTO,
)
from app.application.subscriptions.service import SubscriptionService
from app.domain.subscriptions.entities import (
    BillingCadence,
    Plan,
    SubscriptionStatus,
)
from app.domain.subscriptions.exceptions import (
    InvalidLifecycleTransitionError,
    InvalidSubscriptionReferenceError,
    SubscriptionNotFoundError,
)
from app.infrastructure.database.models.core import (
    SubscriptionModel,
    TransactionModel,
    UsageEventModel,
)
from app.infrastructure.database.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.infrastructure.database.session import get_session

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
)


def get_subscription_service(
    session: AsyncSession = Depends(get_session),
) -> SubscriptionService:
    """Build the subscription service using the request database session."""
    repository = SqlAlchemySubscriptionRepository(session)
    return SubscriptionService(repository)


def convert_plan_input(
    plan_input: PlanInput | None,
) -> Plan | None:
    """Convert an optional API plan into a domain Plan."""
    if plan_input is None:
        return None

    return Plan(
        provider_id=plan_input.provider_id,
        name=plan_input.name,
        amount=plan_input.amount,
        currency=plan_input.currency.upper(),
        billing_interval=BillingCadence(plan_input.billing_interval),
    )


def convert_required_plan_input(plan_input: PlanInput) -> Plan:
    """Convert a validated, non-null plan input into a domain Plan."""
    plan = convert_plan_input(plan_input)

    if plan is None:
        raise ValueError("A plan input is required.")

    return plan


# ---------------------------------------------------------
# Create subscription
# ---------------------------------------------------------


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    dto = CreateSubscriptionDTO(
        user_id=current_user.id,
        name=request.name,
        plan_id=request.plan_id,
        plan=convert_plan_input(request.plan),
        plan_alternatives=[convert_required_plan_input(plan) for plan in request.plan_alternatives],
        status=request.status,
        provider_connection_id=request.provider_connection_id,
        started_at=request.started_at,
        renewal_at=request.renewal_at,
        ended_at=request.ended_at,
    )

    try:
        result = await service.create_subscription(dto, current_user)
        return SubscriptionResponse.model_validate(result)

    except InvalidSubscriptionReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------
# List subscriptions
# ---------------------------------------------------------


@router.get(
    "",
    response_model=SubscriptionListResponse,
)
async def list_subscriptions(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
    size: int | None = Query(None, ge=1, le=100),
    subscription_status: SubscriptionStatus | None = Query(
        None,
        alias="status",
    ),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionListResponse:
    actual_size = page_size or size or 20
    skip = (page - 1) * actual_size

    results, total = await service.list_subscriptions(
        current_user=current_user,
        skip=skip,
        limit=actual_size,
        status=subscription_status,
    )

    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(item) for item in results],
        pagination=PaginationMeta.create(
            page=page,
            page_size=actual_size,
            total_items=total,
        ),
    )


# ---------------------------------------------------------
# Get one subscription
# ---------------------------------------------------------


@router.get(
    "/{id}",
    response_model=SubscriptionResponse,
)
async def get_subscription(
    id: uuid.UUID,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    try:
        result = await service.get_subscription(id, current_user)
        return SubscriptionResponse.model_validate(result)

    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc


# ---------------------------------------------------------
# Update subscription
# ---------------------------------------------------------


@router.patch(
    "/{id}",
    response_model=SubscriptionResponse,
)
async def update_subscription(
    id: uuid.UUID,
    request: SubscriptionUpdateRequest,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    dto = UpdateSubscriptionDTO(
        plan_id=request.plan_id,
        plan=convert_plan_input(request.plan),
        plan_alternatives=(
            [convert_required_plan_input(plan) for plan in request.plan_alternatives]
            if request.plan_alternatives is not None
            else None
        ),
        fields_set=set(request.model_fields_set),
        provider_connection_id=request.provider_connection_id,
        name=request.name,
        status=request.status,
        started_at=request.started_at,
        renewal_at=request.renewal_at,
        ended_at=request.ended_at,
    )

    try:
        result = await service.update_subscription(
            id,
            dto,
            current_user,
        )
        return SubscriptionResponse.model_validate(result)

    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc

    except InvalidSubscriptionReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except InvalidLifecycleTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------
# Delete subscription
# ---------------------------------------------------------


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_subscription(
    id: uuid.UUID,
    current_user: CurrentUser,
    service: SubscriptionService = Depends(get_subscription_service),
) -> None:
    try:
        await service.delete_subscription(id, current_user)

    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc


# ---------------------------------------------------------
# Verify subscription ownership and active record
# ---------------------------------------------------------


async def verify_active_subscription(
    subscription_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> SubscriptionModel:
    subscription = await db.get(
        SubscriptionModel,
        subscription_id,
    )

    if (
        subscription is None
        or subscription.user_id != user_id
        or subscription.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return subscription


# ---------------------------------------------------------
# Ingest transaction
# ---------------------------------------------------------


@router.post(
    "/{id}/transactions",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_transaction(
    id: uuid.UUID,
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await verify_active_subscription(
        id,
        current_user.id,
        db,
    )

    insert_statement = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    statement = insert_statement(TransactionModel).values(
        subscription_id=id,
        user_id=current_user.id,
        amount=payload.amount,
        currency=payload.currency,
        occurred_at=payload.occurrence_time,
        source=payload.source,
        external_reference=payload.external_reference,
    )

    if payload.external_reference is not None:
        statement = statement.on_conflict_do_update(
            index_elements=[
                TransactionModel.user_id,
                TransactionModel.source,
                TransactionModel.external_reference,
            ],
            set_={
                "amount": statement.excluded.amount,
                "currency": statement.excluded.currency,
                "occurred_at": statement.excluded.occurred_at,
            },
        )

    await db.execute(statement)
    await db.commit()

    return {
        "status": "success",
        "message": "Transaction recorded successfully.",
    }


# ---------------------------------------------------------
# Ingest usage event
# ---------------------------------------------------------


@router.post(
    "/usage-events",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_usage_event(
    payload: UsageEventCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await verify_active_subscription(
        payload.subscription_id,
        current_user.id,
        db,
    )

    evidence: dict[str, Any] = {
        "source": payload.source,
        "ingestion_method": "api",
        "ingested_at": datetime.now(UTC).isoformat(),
    }

    if payload.idempotency_key is not None:
        evidence["idempotency_key"] = payload.idempotency_key

    insert_statement = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    statement = insert_statement(UsageEventModel).values(
        subscription_id=payload.subscription_id,
        user_id=current_user.id,
        occurred_at=payload.occurrence_time,
        quantity=payload.quantity,
        is_unknown=payload.is_unknown,
        kind="api_ingestion",
        source=payload.source,
        evidence_json=evidence,
        idempotency_key=payload.idempotency_key,
    )

    if payload.idempotency_key is not None:
        statement = statement.on_conflict_do_nothing(
            index_elements=[
                UsageEventModel.user_id,
                UsageEventModel.source,
                UsageEventModel.idempotency_key,
            ],
        )

    await db.execute(statement)
    await db.commit()

    return {
        "status": "success",
        "message": "Usage event recorded successfully.",
    }
