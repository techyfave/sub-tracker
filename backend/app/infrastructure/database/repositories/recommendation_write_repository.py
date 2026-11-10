
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AnalysisModel,
    RecommendationModel,
    RecommendationEvidenceModel,
    WorkStatus,
)


class RecommendationWriteRepository:
    """
    Writes immutable recommendation snapshots and their evidence.

    Does not commit. Transaction ownership belongs to the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_recommendations(
        self,
        analysis: AnalysisModel,
        recommendations: list[RecommendationModel],
        evidence_rows: list[RecommendationEvidenceModel],
    ) -> None:

        # Verify that every recommendation belongs to this analysis.
        for recommendation in recommendations:
            if recommendation.analysis_id != analysis.id:
                raise ValueError(
                    "Recommendation belongs to another analysis"
                )

            if recommendation.user_id != analysis.user_id:
                raise ValueError(
                    "Recommendation owner does not match analysis owner"
                )

        # Verify evidence ownership.
        recommendation_ids = {
            recommendation.id for recommendation in recommendations
        }

        for evidence in evidence_rows:
            if evidence.user_id != analysis.user_id:
                raise ValueError(
                    "Evidence owner does not match analysis owner"
                )

            if evidence.recommendation_id not in recommendation_ids:
                raise ValueError(
                    "Evidence references an unknown recommendation"
                )

        # Add all recommendations.
        self.session.add_all(recommendations)
        await self.session.flush()

        # Add all supporting evidence.
        self.session.add_all(evidence_rows)
        await self.session.flush()

        # Only mark completed after all inserts succeed.
        analysis.status = WorkStatus.COMPLETED

        await self.session.flush()
