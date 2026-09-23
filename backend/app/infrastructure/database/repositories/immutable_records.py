from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AuditEventModel, RecommendationModel


class RecommendationRepository:
    """Persistence access for immutable recommendation snapshots.

    Deliberately exposes creation and retrieval only. Corrections and
    re-analysis create a new version rather than updating a snapshot.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, recommendation_id: uuid.UUID) -> RecommendationModel | None:
        return await self._session.get(RecommendationModel, recommendation_id)

    async def add(self, recommendation: RecommendationModel) -> RecommendationModel:
        self._session.add(recommendation)
        await self._session.flush()
        return recommendation


class AuditEventRepository:
    """Append-only persistence access for audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: uuid.UUID) -> AuditEventModel | None:
        return await self._session.get(AuditEventModel, event_id)

    async def append(self, event: AuditEventModel) -> AuditEventModel:
        self._session.add(event)
        await self._session.flush()
        return event
