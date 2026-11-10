
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AnalysisModel,
    WorkStatus,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import SubscriptionModel

# Replace this import with your project's actual authentication dependency.
from app.api.v1.dependencies import get_current_user


router = APIRouter(
    prefix="/analyses",
    tags=["Analyses"],
)


# --------------------------------------------------
# REQUEST AND RESPONSE SCHEMAS
# --------------------------------------------------

class AnalysisCreateRequest(BaseModel):
    subscription_id: uuid.UUID


class AnalysisCreateResponse(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subscription_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None


# --------------------------------------------------
# POST /api/v1/analyses
# --------------------------------------------------

@router.post(
    "",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis(
    payload: AnalysisCreateRequest,
    response: Response,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user.id

    # 1. Check whether this request already exists.
    existing_query = select(AnalysisModel).where(
        AnalysisModel.user_id == user_id,
        AnalysisModel.idempotency_key == idempotency_key,
    )

    existing_result = await session.execute(existing_query)
    existing_analysis = existing_result.scalar_one_or_none()

    if existing_analysis is not None:
        # A repeated key with a different subscription is a conflict.
        if existing_analysis.subscription_id != payload.subscription_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was already used for another request.",
            )

        response.status_code = status.HTTP_202_ACCEPTED

        return AnalysisCreateResponse(
            id=existing_analysis.id,
            status=existing_analysis.status.value,
            created_at=existing_analysis.created_at,
        )

    # 2. Verify that the subscription belongs to this user.
    subscription_query = select(SubscriptionModel).where(
        SubscriptionModel.id == payload.subscription_id,
        SubscriptionModel.user_id == user_id,
    )

    subscription_result = await session.execute(subscription_query)
    subscription = subscription_result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    # 3. Create the analysis.
    analysis = AnalysisModel(
        id=uuid.uuid4(),
        user_id=user_id,
        subscription_id=payload.subscription_id,
        idempotency_key=idempotency_key,
        status=WorkStatus.QUEUED,
    )

    try:
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

    except Exception:
        await session.rollback()

        # Handle a concurrent request using the same key.
        existing_query = select(AnalysisModel).where(
            AnalysisModel.user_id == user_id,
            AnalysisModel.idempotency_key == idempotency_key,
        )

        existing_result = await session.execute(existing_query)
        existing_analysis = existing_result.scalar_one_or_none()

        if existing_analysis is not None:
            if existing_analysis.subscription_id != payload.subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key was already used for another request.",
                )

            response.status_code = status.HTTP_202_ACCEPTED

            return AnalysisCreateResponse(
                id=existing_analysis.id,
                status=existing_analysis.status.value,
                created_at=existing_analysis.created_at,
            )

        raise

    # 4. Enqueue the worker here.
    #
    # IMPORTANT:
    # Do not leave this as an unprotected direct enqueue in production.
    # Use a transactional outbox so a broker failure cannot leave
    # an analysis permanently queued.
    #
    # Example:
    # process_analysis.delay(str(analysis.id))

    return AnalysisCreateResponse(
        id=analysis.id,
        status=analysis.status.value,
        created_at=analysis.created_at,
    )


# --------------------------------------------------
# GET /api/v1/analyses/{analysis_id}
# --------------------------------------------------

@router.get(
    "/{analysis_id}",
    response_model=AnalysisStatusResponse,
)
async def get_analysis(
    analysis_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(AnalysisModel).where(
        AnalysisModel.id == analysis_id,
        AnalysisModel.user_id == current_user.id,
    )

    result = await session.execute(query)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    return AnalysisStatusResponse(
        id=analysis.id,
        subscription_id=analysis.subscription_id,
        status=analysis.status.value,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        failure_code=analysis.failure_code,
        failure_message=analysis.failure_message,
    )
