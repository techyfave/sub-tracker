import uuid  # unique ids
from typing import Annotated  # dependency and query annotations

from fastapi import APIRouter, Depends, Query  # web framework pieces
from sqlalchemy.ext.asyncio import AsyncSession  # async DB session

from app.api.problem_details import raise_problem  # shared Problem Details raiser
from app.api.v1.dependencies.auth import CurrentUser  # logged-in user dependency
from app.api.v1.schemas.common import MoneySchema, PaginationMeta  # shared schemas
from app.api.v1.schemas.recommendation import (  # response schemas and projections
    AnalysisState,  # analysis state
    AnalysisStatus,  # public analysis states
    EvidenceResponse,  # one piece of evidence
    RecommendationListResponse,  # list response
    RecommendationResponse,  # single response
    SavingsInfo,  # savings
    UncertaintyInfo,  # uncertainty
    VersionInfo,  # versions
    public_snapshot,  # allowlisted evidence projection
    public_uncertainty,  # allowlisted uncertainty projection
    to_public_status,  # stored status -> public status
    to_stored_status,  # public status -> stored status
)
from app.application.recommendations.service import RecommendationService  # business logic
from app.domain.recommendations.entities import Recommendation  # domain record
from app.domain.recommendations.exceptions import RecommendationNotFoundError  # missing record
from app.infrastructure.database.models import RecommendationAction  # action enum
from app.infrastructure.database.repositories.recommendation_read_repository import (
    SqlAlchemyRecommendationReadRepository,  # concrete storage
)
from app.infrastructure.database.session import get_session  # session dependency

# all routes live under /recommendations
router = APIRouter(
    prefix="/recommendations",  # URL prefix
    tags=["Recommendations"],  # docs grouping
)


def get_recommendation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecommendationService:
    # build read-only storage on the request's session
    repository = SqlAlchemyRecommendationReadRepository(session)
    # build the service on that storage
    return RecommendationService(repository)


def to_response(item: Recommendation) -> RecommendationResponse:
    # project the stored uncertainty JSON down to its public fields
    uncertainty = public_uncertainty(item.uncertainty)
    # build the response explicitly, so only chosen fields can ever leave the API
    return RecommendationResponse(
        id=item.id,  # id
        recommended_action=RecommendationAction(item.recommended_action),  # action
        rationale=item.rationale,  # explanation
        versions=VersionInfo(
            recommendation_version=item.version,  # recommendation version
            prompt_version=item.prompt_version,  # prompt version
            schema_version=item.schema_version,  # schema version
        ),
        analysis=AnalysisState(
            analysis_id=item.analysis_id,  # analysis id
            subscription_id=item.subscription_id,  # subscription id
            status=to_public_status(item.analysis_status),  # public analysis state
            completed_at=item.analysis_completed_at,  # completion time
        ),
        uncertainty=UncertaintyInfo(
            confidence=item.confidence,  # confidence
            level=uncertainty["level"],  # public level
            reason=uncertainty["reason"],  # public reason
        ),
        savings=SavingsInfo(
            monthly=MoneySchema(amount=item.monthly_savings_amount, currency=item.currency),
            annual=MoneySchema(amount=item.annual_savings_amount, currency=item.currency),
        ),
        evidence=[
            EvidenceResponse(
                id=piece.id,  # evidence id
                evidence_type=piece.evidence_type,  # kind
                source_table=piece.source_table,  # origin table
                source_id=piece.source_id,  # origin row
                snapshot=public_snapshot(piece.snapshot),  # allowlisted summary only
                created_at=piece.created_at,  # recorded time
            )
            for piece in item.evidence
        ],
        created_at=item.created_at,  # creation time
    )


@router.get(
    "",  # GET /recommendations
    response_model=RecommendationListResponse,  # response shape
)
async def list_recommendations(
    current_user: CurrentUser,  # logged-in user
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],  # logic
    page: int = Query(1, ge=1),  # page number
    page_size: int = Query(20, ge=1, le=100),  # page size
    status: Annotated[
        AnalysisStatus | None,
        Query(description="Analysis state: queued, running, completed or failed"),
    ] = None,
    action: Annotated[RecommendationAction | None, Query(description="Recommended action")] = None,
    subscription_id: Annotated[uuid.UUID | None, Query()] = None,  # subscription filter
) -> RecommendationListResponse:
    # convert page number to row offset
    skip = (page - 1) * page_size
    # fetch the page and the total; the public status is translated to the stored one first
    items, total = await service.list_recommendations(
        current_user=current_user,  # whose
        skip=skip,  # offset
        limit=page_size,  # page size
        status=to_stored_status(status) if status is not None else None,  # status filter
        action=action.value if action is not None else None,  # action filter
        subscription_id=subscription_id,  # subscription filter
    )
    # wrap in the paginated envelope
    return RecommendationListResponse(
        items=[to_response(item) for item in items],  # rows
        pagination=PaginationMeta.create(
            page=page,  # current page
            page_size=page_size,  # page size
            total_items=total,  # total rows
        ),
    )


@router.get(
    "/{recommendation_id}",  # GET /recommendations/{id}
    response_model=RecommendationResponse,  # response shape
)
async def get_recommendation(
    recommendation_id: uuid.UUID,  # path id
    current_user: CurrentUser,  # logged-in user
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],  # logic
) -> RecommendationResponse:
    # translate the domain error into Problem Details
    try:
        # fetch it, scoped to the caller
        item = await service.get_recommendation(recommendation_id, current_user=current_user)
    except RecommendationNotFoundError as exc:
        # same 404 for missing and foreign ids
        raise_problem(
            status_code=404,
            title="Not Found",
            detail=str(exc),
            type_name="not-found",
        )
    # return the safe response
    return to_response(item)
