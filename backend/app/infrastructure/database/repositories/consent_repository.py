from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AuditEventModel, ConsentModel


class SqlAlchemyConsentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, policy_version: str, scopes: list[str]
    ) -> ConsentModel:
        consent = ConsentModel(
            user_id=user_id,
            policy_version=policy_version,
            scopes=scopes,
            granted_at=datetime.now(UTC),
            revoked_at=None,
        )
        self.session.add(consent)
        await self.session.flush()
        return consent

    async def list_for_user(self, user_id: uuid.UUID) -> list[ConsentModel]:
        result = await self.session.scalars(
            select(ConsentModel)
            .where(ConsentModel.user_id == user_id)
            .order_by(ConsentModel.granted_at.desc())
        )
        return list(result.all())

    async def revoke(self, *, consent_id: uuid.UUID, user_id: uuid.UUID) -> ConsentModel | None:
        # Lock the row where supported so concurrent revocations observe the first timestamp.
        result = await self.session.execute(
            select(ConsentModel).where(ConsentModel.id == consent_id).with_for_update()
        )
        consent = result.scalar_one_or_none()
        if consent is None:
            return None
        if consent.user_id != user_id:
            from app.api.problem_details import raise_problem

            raise_problem(
                status_code=403,
                title="Forbidden",
                detail="You do not have access to this resource.",
            )
        if consent.revoked_at is None:
            now = datetime.now(UTC)
            consent.revoked_at = now
            self.session.add(
                AuditEventModel(
                    user_id=user_id,
                    event_type="consent.revoked",
                    actor_type="user",
                    actor_id=user_id,
                    resource_type="consent",
                    resource_id=consent.id,
                    correlation_id=None,
                    payload_json={
                        "policy_version": consent.policy_version,
                        "scopes": consent.scopes,
                    },
                    occurred_at=now,
                )
            )
            await self.session.flush()
        return consent
