
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.models import AnalysisModel
from app.infrastructure.database.repositories.recommendation_write_repository import (
    RecommendationWriteRepository,
)


class AnalysisWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        evidence_loader,
        feature_calculator,
        recommendation_pipeline,
        recommendation_mapper,
    ) -> None:
        self.session_factory = session_factory
        self.evidence_loader = evidence_loader
        self.feature_calculator = feature_calculator
        self.recommendation_pipeline = recommendation_pipeline
        self.recommendation_mapper = recommendation_mapper

    async def execute(self, analysis_id: UUID) -> None:

        # 1. Retrieve analysis and evidence.
        async with self.session_factory() as session:
            analysis = await session.get(AnalysisModel, analysis_id)

            if analysis is None:
                raise ValueError("Analysis not found")

            user_id = analysis.user_id
            subscription_id = analysis.subscription_id

            evidence = await self.evidence_loader.load(
                session=session,
                user_id=user_id,
                subscription_id=subscription_id,
            )

        if not evidence:
            raise ValueError("No evidence available for analysis")

        # 2. Calculate deterministic features.
        features = self.feature_calculator.calculate(evidence)

        # 3. Generate recommendations using the validated pipeline.
        # This must return validated domain contracts, not raw AI output.
        validated = await self.recommendation_pipeline.generate(
            features=features,
            evidence=evidence,
        )

        # 4. Convert validated contracts into persistence models.
        recommendations, evidence_rows = (
            self.recommendation_mapper.to_models(
                analysis_id=analysis_id,
                user_id=user_id,
                validated=validated,
            )
        )

        # 5. Persist everything atomically.
        async with self.session_factory() as session:
            async with session.begin():

                analysis = await session.get(
                    AnalysisModel,
                    analysis_id,
                    with_for_update=True,
                )

                if analysis is None:
                    raise ValueError("Analysis not found")

                if analysis.user_id != user_id:
                    raise PermissionError("Analysis ownership changed")

                writer = RecommendationWriteRepository(session)

                await writer.save_recommendations(
                    analysis=analysis,
                    recommendations=recommendations,
                    evidence_rows=evidence_rows,
                )
