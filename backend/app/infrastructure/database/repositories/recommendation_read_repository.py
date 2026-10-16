import uuid  # unique ids

from sqlalchemy import ColumnElement, and_, func, select  # query builders
from sqlalchemy.ext.asyncio import AsyncSession  # async DB session

from app.domain.recommendations.entities import (  # domain records
    Recommendation,  # recommendation snapshot
    RecommendationEvidence,  # one piece of evidence
)
from app.infrastructure.database.models import (  # DB models and enums
    AnalysisModel,  # analyses table
    RecommendationAction,  # action enum
    RecommendationEvidenceModel,  # evidence table
    RecommendationModel,  # recommendations table
    WorkStatus,  # analysis status enum
)

# stored analysis states the public vocabulary cannot express yet; their recommendations
# are hidden until issue #13 decides how to publish them
UNPUBLISHED_ANALYSIS_STATUSES: list[WorkStatus] = [WorkStatus.CANCELLED]


class SqlAlchemyRecommendationReadRepository:
    """Read-only access to recommendation snapshots. It never writes."""

    def __init__(self, session: AsyncSession):
        # keep the session for every query
        self.session = session

    @staticmethod
    def _to_entity(
        recommendation: RecommendationModel,  # recommendation row
        analysis: AnalysisModel,  # its analysis row
        evidence: list[RecommendationEvidence],  # its evidence
    ) -> Recommendation:
        # copy only the fields we choose to expose
        return Recommendation(
            id=recommendation.id,  # id
            analysis_id=recommendation.analysis_id,  # analysis id
            subscription_id=analysis.subscription_id,  # subscription it is about
            analysis_status=analysis.status.value,  # analysis state as text
            analysis_completed_at=analysis.completed_at,  # when the analysis finished
            version=recommendation.version,  # recommendation version
            recommended_action=recommendation.recommended_action.value,  # action as text
            confidence=recommendation.confidence,  # confidence
            rationale=recommendation.rationale,  # explanation
            uncertainty=recommendation.uncertainty_json,  # uncertainty details
            monthly_savings_amount=recommendation.monthly_savings_amount,  # monthly savings
            annual_savings_amount=recommendation.annual_savings_amount,  # annual savings
            currency=recommendation.currency,  # currency
            prompt_version=recommendation.prompt_version,  # prompt version
            schema_version=recommendation.schema_version,  # schema version
            created_at=recommendation.created_at,  # creation time
            evidence=evidence,  # supporting evidence
        )

    async def _evidence_for(
        self,
        recommendation_ids: list[uuid.UUID],  # recommendations on this page
        user_id: uuid.UUID,  # owner
    ) -> dict[uuid.UUID, list[RecommendationEvidence]]:
        # nothing to load for an empty page
        if not recommendation_ids:
            # return an empty map
            return {}
        # one query for all evidence on the page, owner-scoped
        query = (
            select(RecommendationEvidenceModel)
            .where(
                and_(
                    RecommendationEvidenceModel.recommendation_id.in_(recommendation_ids),  # page
                    RecommendationEvidenceModel.user_id == user_id,  # owner
                )
            )
            .order_by(RecommendationEvidenceModel.created_at, RecommendationEvidenceModel.id)
        )
        # run the query
        result = await self.session.execute(query)
        # group evidence by recommendation
        grouped: dict[uuid.UUID, list[RecommendationEvidence]] = {}
        # walk every evidence row
        for row in result.scalars().all():
            # add it under its recommendation id
            grouped.setdefault(row.recommendation_id, []).append(
                RecommendationEvidence(
                    id=row.id,  # evidence id
                    evidence_type=row.evidence_type,  # kind
                    source_table=row.source_table,  # origin table
                    source_id=row.source_id,  # origin row
                    snapshot=row.snapshot_json,  # frozen evidence
                    created_at=row.created_at,  # recorded time
                )
            )
        # hand back the map
        return grouped

    async def get_by_id(
        self,
        recommendation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Recommendation | None:
        # match id and owner on both tables
        query = (
            select(RecommendationModel, AnalysisModel)
            .join(AnalysisModel, AnalysisModel.id == RecommendationModel.analysis_id)
            .where(
                and_(
                    RecommendationModel.id == recommendation_id,  # right row
                    RecommendationModel.user_id == user_id,  # right owner
                    AnalysisModel.user_id == user_id,  # analysis has the same owner
                    AnalysisModel.status.not_in(UNPUBLISHED_ANALYSIS_STATUSES),  # hide unpublished
                )
            )
        )
        # run the query
        result = await self.session.execute(query)
        # zero or one row
        row = result.first()
        # nothing found
        if row is None:
            # signal absence
            return None
        # split the pair
        recommendation, analysis = row
        # load its evidence
        evidence = await self._evidence_for([recommendation.id], user_id)
        # build the domain record
        return self._to_entity(recommendation, analysis, evidence.get(recommendation.id, []))

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        action: str | None = None,
        subscription_id: uuid.UUID | None = None,
    ) -> tuple[list[Recommendation], int]:
        # always filter by owner
        conditions: list[ColumnElement[bool]] = [
            RecommendationModel.user_id == user_id,  # right owner
            AnalysisModel.user_id == user_id,  # analysis has the same owner
            AnalysisModel.status.not_in(UNPUBLISHED_ANALYSIS_STATUSES),  # hide unpublished
        ]

        # optional analysis status filter
        if status is not None:
            # convert text to the DB enum
            conditions.append(AnalysisModel.status == WorkStatus(status))
        # optional action filter
        if action is not None:
            # convert the text to the action enum
            action_enum = RecommendationAction(action)
            # match the recommended action
            conditions.append(RecommendationModel.recommended_action == action_enum)
        # optional subscription filter
        if subscription_id is not None:
            # match the analysis subscription
            conditions.append(AnalysisModel.subscription_id == subscription_id)
        # count every matching row
        count_query = (
            select(func.count())
            .select_from(RecommendationModel)
            .join(AnalysisModel, AnalysisModel.id == RecommendationModel.analysis_id)
            .where(and_(*conditions))
        )
        # run the count
        total = (await self.session.execute(count_query)).scalar_one()
        # fetch one page, newest first, with a stable tie-break
        page_query = (
            select(RecommendationModel, AnalysisModel)
            .join(AnalysisModel, AnalysisModel.id == RecommendationModel.analysis_id)
            .where(and_(*conditions))
            .order_by(RecommendationModel.created_at.desc(), RecommendationModel.id.desc())
            .offset(skip)  # skip earlier pages
            .limit(limit)  # page size
        )
        # run the query
        rows = (await self.session.execute(page_query)).all()
        # ids of the recommendations on this page
        page_ids = [recommendation.id for recommendation, _ in rows]
        # load evidence for the whole page at once
        evidence = await self._evidence_for(page_ids, user_id)
        # convert every row to a domain record
        items = [
            self._to_entity(recommendation, analysis, evidence.get(recommendation.id, []))
            for recommendation, analysis in rows
        ]
        # return the page and the total
        return items, total
