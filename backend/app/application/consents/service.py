from __future__ import annotations

import uuid

from app.infrastructure.database.models import ConsentModel
from app.infrastructure.database.repositories.consent_repository import SqlAlchemyConsentRepository


class ConsentService:
    def __init__(self, repository: SqlAlchemyConsentRepository) -> None:
        self.repository = repository

    async def grant(
        self,
        *,
        user_id: uuid.UUID,
        policy_version: str,
        scopes: list[str],
    ) -> ConsentModel:
        return await self.repository.create(
            user_id=user_id,
            policy_version=policy_version,
            scopes=scopes,
        )

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[ConsentModel]:
        return await self.repository.list_for_user(user_id)

    async def revoke(self, *, consent_id: uuid.UUID, user_id: uuid.UUID) -> ConsentModel | None:
        return await self.repository.revoke(consent_id=consent_id, user_id=user_id)
