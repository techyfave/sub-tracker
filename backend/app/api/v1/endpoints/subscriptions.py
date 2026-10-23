import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.openapi_responses import (
    PROBLEM_401,
    SAMPLE_SUBSCRIPTION_PATH,
    SAMPLE_TRANSACTION_PATH,
    SUBSCRIPTION_CREATE_422,
    SUBSCRIPTION_ITEM_404,
    SUBSCRIPTION_LIST_VALIDATION_ERROR_EXAMPLE,
    SUBSCRIPTION_PATH_VALIDATION_ERROR_EXAMPLE,
    SUBSCRIPTION_UPDATE_400,
    SUBSCRIPTION_UPDATE_422,
    TRANSACTION_CONFLICT_409,
    TRANSACTION_VALIDATION_ERROR_EXAMPLE,
    USAGE_EVENT_422,
    USAGE_EVENT_CONFLICT_409,
    problem_response,
    response_with_instance,
)
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


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            "/api/v1/subscriptions",
        ),
        422: SUBSCRIPTION_CREATE_422,
    },
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


@router.get(
    "",
    response_model=SubscriptionListResponse,
    responses={
        200: {
            "description": ("Paginated subscriptions belonging to the authenticated user."),
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174003",
                                "user_id": "123e4567-e89b-12d3-a456-426614174004",
                                "plan_id": "123e4567-e89b-12d3-a456-426614174002",
                                "plan": {
                                    "id": "123e4567-e89b-12d3-a456-426614174002",
                                    "provider_id": ("123e4567-e89b-12d3-a456-426614174001"),
                                    "name": "Monthly Premium",
                                    "amount": "5000.00",
                                    "currency": "NGN",
                                    "billing_interval": "monthly",
                                },
                                "plan_alternatives": [],
                                "provider_connection_id": None,
                                "name": "Music Subscription",
                                "status": "active",
                                "started_at": "2026-10-01T10:00:00Z",
                                "renewal_at": "2026-11-01T10:00:00Z",
                                "ended_at": None,
                                "created_at": "2026-10-01T10:00:00Z",
                                "updated_at": "2026-10-01T10:00:00Z",
                                "deleted_at": None,
                            }
                        ],
                        "pagination": {
                            "page": 1,
                            "page_size": 20,
                            "total_items": 1,
                            "total_pages": 1,
                        },
                    }
                }
            },
        },
        401: response_with_instance(
            PROBLEM_401,
            "/api/v1/subscriptions",
        ),
        422: problem_response(
            "The request contains invalid query parameters.",
            SUBSCRIPTION_LIST_VALIDATION_ERROR_EXAMPLE,
            instance="/api/v1/subscriptions",
        ),
    },
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


@router.get(
    "/{id}",
    response_model=SubscriptionResponse,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            SAMPLE_SUBSCRIPTION_PATH,
        ),
        404: SUBSCRIPTION_ITEM_404,
        422: problem_response(
            "The request contains an invalid subscription ID.",
            SUBSCRIPTION_PATH_VALIDATION_ERROR_EXAMPLE,
            instance=SAMPLE_SUBSCRIPTION_PATH,
        ),
    },
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


@router.patch(
    "/{id}",
    response_model=SubscriptionResponse,
    responses={
        400: SUBSCRIPTION_UPDATE_400,
        401: response_with_instance(
            PROBLEM_401,
            SAMPLE_SUBSCRIPTION_PATH,
        ),
        404: SUBSCRIPTION_ITEM_404,
        422: SUBSCRIPTION_UPDATE_422,
    },
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


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            SAMPLE_SUBSCRIPTION_PATH,
        ),
        404: SUBSCRIPTION_ITEM_404,
        422: problem_response(
            "The request contains an invalid subscription ID.",
            SUBSCRIPTION_PATH_VALIDATION_ERROR_EXAMPLE,
            instance=SAMPLE_SUBSCRIPTION_PATH,
        ),
    },
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


async def verify_active_subscription(
    subscription_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> SubscriptionModel:
    """Ensure a subscription exists, belongs to the user, and is not deleted."""
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


@router.post(
    "/{id}/transactions",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            SAMPLE_TRANSACTION_PATH,
        ),
        404: problem_response(
            "The subscription was not found.",
            {
                "type": "about:blank",
                "title": "HTTP Error",
                "status": 404,
                "detail": "Subscription not found",
                "instance": SAMPLE_TRANSACTION_PATH,
            },
            instance=SAMPLE_TRANSACTION_PATH,
        ),
        409: TRANSACTION_CONFLICT_409,
        422: problem_response(
            "The request contains an invalid subscription ID.",
            TRANSACTION_VALIDATION_ERROR_EXAMPLE,
            instance=SAMPLE_TRANSACTION_PATH,
        ),
    },
)
async def ingest_transaction(
    id: uuid.UUID,
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await verify_active_subscription(id, current_user.id, db)

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
            where=TransactionModel.subscription_id == id,
        )

    result = await db.execute(statement.returning(TransactionModel.id))
    transaction_id = result.scalar_one_or_none()

    if transaction_id is None:
        if payload.external_reference is not None:
            existing_result = await db.execute(
                select(TransactionModel.subscription_id).where(
                    TransactionModel.user_id == current_user.id,
                    TransactionModel.source == payload.source,
                    TransactionModel.external_reference == payload.external_reference,
                )
            )
            existing_subscription_id = existing_result.scalar_one_or_none()
        else:
            existing_subscription_id = None

        await db.rollback()

        if existing_subscription_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This transaction reference is already associated with another subscription."
                ),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The transaction could not be recorded safely.",
        )

    await db.commit()

    return {
        "status": "success",
        "message": "Transaction recorded successfully.",
    }


@router.post(
    "/usage-events",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: response_with_instance(
            PROBLEM_401,
            "/api/v1/subscriptions/usage-events",
        ),
        404: problem_response(
            "The subscription was not found.",
            {
                "type": "about:blank",
                "title": "HTTP Error",
                "status": 404,
                "detail": "Subscription not found",
                "instance": "/api/v1/subscriptions/usage-events",
            },
            instance="/api/v1/subscriptions/usage-events",
        ),
        409: USAGE_EVENT_CONFLICT_409,
        422: USAGE_EVENT_422,
    },
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

    result = await db.execute(statement.returning(UsageEventModel.id))
    event_id = result.scalar_one_or_none()

    if event_id is None:
        if payload.idempotency_key is None:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The usage event could not be recorded safely.",
            )

        existing_result = await db.execute(
            select(UsageEventModel).where(
                UsageEventModel.user_id == current_user.id,
                UsageEventModel.source == payload.source,
                UsageEventModel.idempotency_key == payload.idempotency_key,
            )
        )
        existing_event = existing_result.scalar_one_or_none()

        if existing_event is None:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The idempotency conflict could not be resolved safely.",
            )

        if existing_event.subscription_id != payload.subscription_id:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This idempotency key is already associated with another subscription."),
            )

        existing_time = existing_event.occurred_at
        requested_time = payload.occurrence_time

        if existing_time.tzinfo is None:
            existing_time = existing_time.replace(tzinfo=UTC)
        else:
            existing_time = existing_time.astimezone(UTC)

        requested_time = requested_time.astimezone(UTC)

        same_payload = (
            existing_time == requested_time
            and existing_event.quantity == payload.quantity
            and existing_event.is_unknown == payload.is_unknown
        )

        if not same_payload:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This idempotency key was already used with a different usage payload."),
            )

    await db.commit()

    return {
        "status": "success",
        "message": "Usage event recorded successfully.",
    }
