import uuid  # unique ids
from typing import Protocol  # interface base

from app.domain.recommendations.entities import Recommendation  # domain record


class RecommendationReadRepository(Protocol):  # what any storage backend must provide
    async def get_by_id(
        self, recommendation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Recommendation | None:
        # fetch one recommendation owned by this user
        ...

    async def list_by_user(
        self,
        user_id: uuid.UUID,  # whose recommendations
        skip: int = 0,  # rows to skip
        limit: int = 20,  # page size
        status: str | None = None,  # analysis status filter
        action: str | None = None,  # recommended action filter
        subscription_id: uuid.UUID | None = None,  # subscription filter
    ) -> tuple[list[Recommendation], int]:
        # fetch one page plus the total count
        ...
