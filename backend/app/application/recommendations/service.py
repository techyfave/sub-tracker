import uuid  # unique ids

from app.domain.recommendations.entities import Recommendation  # domain record
from app.domain.recommendations.exceptions import RecommendationNotFoundError  # missing record
from app.domain.recommendations.repositories import (
    RecommendationReadRepository,  # storage interface
)
from app.domain.users.entities import User  # current user type


class RecommendationService:
    def __init__(self, repository: RecommendationReadRepository):
        # keep the repository for every operation
        self.repository = repository

    async def get_recommendation(
        self,
        recommendation_id: uuid.UUID,
        current_user: User,
    ) -> Recommendation:
        # fetch only this user's recommendation
        recommendation = await self.repository.get_by_id(
            recommendation_id=recommendation_id,  # which one
            user_id=current_user.id,  # whose
        )
        # missing or not theirs
        if recommendation is None:
            # same 404 for both, so ids do not leak
            raise RecommendationNotFoundError(str(recommendation_id))
        # hand it back
        return recommendation

    async def list_recommendations(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        action: str | None = None,
        subscription_id: uuid.UUID | None = None,
    ) -> tuple[list[Recommendation], int]:
        # fetch one page for this user only
        return await self.repository.list_by_user(
            user_id=current_user.id,  # whose
            skip=skip,  # offset
            limit=limit,  # page size
            status=status,  # optional filter
            action=action,  # optional filter
            subscription_id=subscription_id,  # optional filter
        )
