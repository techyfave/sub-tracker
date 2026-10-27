"""Authenticated analysis creation and polling APIs."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.problem_details import raise_problem
from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.schemas.recommendation import AnalysisStatus, to_public_status
from app.application.analyses.service import AnalysisInputError, create_analysis
from app.application.jobs import IdempotencyConflict
from app.infrastructure.database.models.core import AnalysisModel
from app.infrastructure.database.session import get_session

router = APIRouter(prefix="/analyses", tags=["Analyses"])
Session = Annotated[AsyncSession, Depends(get_session)]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subscription_id: UUID


class AnalysisResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    status: AnalysisStatus
    attempt_count: int
    failure_code: str | None
    started_at: datetime | None
    completed_at: datetime | None


def response_for(item: AnalysisModel) -> AnalysisResponse:
    return AnalysisResponse(
        id=item.id,
        subscription_id=item.subscription_id,
        status=to_public_status(item.status),
        attempt_count=item.attempt_count,
        failure_code=item.failure_code,
        started_at=item.started_at,
        completed_at=item.completed_at,
    )


@router.post("", response_model=AnalysisResponse, status_code=202)
async def request_analysis(
    body: AnalysisRequest,
    current_user: CurrentUser,
    session: Session,
    response: Response,
    request: Request,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255, pattern=r".*\S.*")],
) -> AnalysisResponse:
    try:
        item = await create_analysis(
            session, current_user.id, body.subscription_id, idempotency_key
        )
    except LookupError:
        raise_problem(status_code=404, title="Not Found", detail="Subscription not found")
    except IdempotencyConflict as exc:
        raise_problem(status_code=409, title="Conflict", detail=str(exc))
    except AnalysisInputError as exc:
        raise_problem(status_code=422, title="Analysis unavailable", detail=str(exc))
    response.headers["Location"] = request.url_for("get_analysis", analysis_id=str(item.id)).path
    return response_for(item)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID, current_user: CurrentUser, session: Session
) -> AnalysisResponse:
    item = await session.scalar(
        select(AnalysisModel).where(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == current_user.id,
        )
    )
    if item is None:
        raise_problem(status_code=404, title="Not Found", detail="Analysis not found")
    return response_for(item)
