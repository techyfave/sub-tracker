from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.database.models.core import (
    PlanModel,
    ProviderModel,
    SubscriptionModel,
    TransactionModel,
    UsageEventModel,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_session
from app.main import app

pytestmark = pytest.mark.asyncio

SUBSCRIPTIONS_PATH = "/api/v1/subscriptions"
USAGE_EVENTS_PATH = f"{SUBSCRIPTIONS_PATH}/usage-events"
TEST_PREFIX = "issue8-pg-"


def _async_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql+asyncpg://"):
        return raw_url
    if raw_url.startswith("postgresql://"):
        return raw_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )
    if raw_url.startswith("postgres://"):
        return raw_url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )
    pytest.fail("TEST_DATABASE_URL must use a PostgreSQL URL supported by asyncpg.")


def _upgrade_database(database_url: str) -> None:
    """Run Alembic in a worker thread's synchronous function."""
    repository_root = Path(__file__).resolve().parents[3]
    migration_env = {
        **os.environ,
        "DATABASE_URL": database_url,
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=repository_root,
        env=migration_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not upgrade the dedicated PostgreSQL test database.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


@pytest.fixture
async def postgres_context() -> AsyncIterator[tuple[AsyncClient, async_sessionmaker[AsyncSession]]]:
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL ingestion tests")

    database_url = _async_database_url(raw_url)
    await asyncio.to_thread(_upgrade_database, database_url)

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    previous_override = app.dependency_overrides.get(get_session)

    async def postgres_session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = postgres_session_override

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://postgres-test",
        ) as client:
            yield client, session_factory
    finally:
        try:
            async with session_factory() as session:
                await session.execute(
                    delete(UserModel).where(UserModel.email.like(f"{TEST_PREFIX}%"))
                )

                provider_ids = list(
                    (
                        await session.scalars(
                            select(ProviderModel.id).where(
                                ProviderModel.slug.like(f"{TEST_PREFIX}provider-%")
                            )
                        )
                    ).all()
                )

                if provider_ids:
                    await session.execute(
                        delete(PlanModel).where(PlanModel.provider_id.in_(provider_ids))
                    )
                    await session.execute(
                        delete(ProviderModel).where(ProviderModel.id.in_(provider_ids))
                    )

                await session.commit()
        finally:
            if previous_override is None:
                app.dependency_overrides.pop(get_session, None)
            else:
                app.dependency_overrides[get_session] = previous_override
            await engine.dispose()


async def _register_and_login(client: AsyncClient) -> dict[str, str]:
    email = f"{TEST_PREFIX}{uuid.uuid4().hex}@example.com"
    password = "correct-horse-test-password"

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text

    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_subscription(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    headers: dict[str, str],
) -> str:
    provider = ProviderModel(
        slug=f"{TEST_PREFIX}provider-{uuid.uuid4().hex}",
        display_name="Issue 8 PostgreSQL Test Provider",
    )
    async with session_factory() as session:
        session.add(provider)
        await session.commit()
        provider_id = str(provider.id)

    response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers=headers,
        json={
            "name": "Issue 8 PostgreSQL Test Subscription",
            "plan": {
                "provider_id": provider_id,
                "name": "PostgreSQL Test Monthly Plan",
                "amount": "9.99",
                "currency": "USD",
                "billing_interval": "monthly",
            },
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _transaction_payload(
    *,
    amount: str = "10.00",
    external_reference: str = "pg-transaction-001",
) -> dict[str, str]:
    return {
        "amount": amount,
        "currency": "USD",
        "occurrence_time": datetime.now(UTC).isoformat(),
        "source": "review41",
        "external_reference": external_reference,
    }


def _usage_payload(
    subscription_id: str,
    *,
    idempotency_key: str = "pg-usage-001",
    quantity: str = "1.2500",
) -> dict[str, object]:
    return {
        "subscription_id": subscription_id,
        "occurrence_time": datetime.now(UTC).isoformat(),
        "quantity": quantity,
        "is_unknown": False,
        "source": "review41",
        "idempotency_key": idempotency_key,
    }


async def test_postgres_transaction_collision_does_not_modify_other_subscription(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_a = await _create_subscription(client, factory, headers)
    subscription_b = await _create_subscription(client, factory, headers)
    reference = f"collision-{uuid.uuid4().hex}"

    first_payload = _transaction_payload(
        amount="10.00",
        external_reference=reference,
    )
    first_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_a}/transactions",
        headers=headers,
        json=first_payload,
    )
    assert first_response.status_code == 201, first_response.text

    collision_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_b}/transactions",
        headers=headers,
        json={**first_payload, "amount": "99.00"},
    )
    assert collision_response.status_code == 409, collision_response.text

    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(TransactionModel).where(
                        TransactionModel.source == "review41",
                        TransactionModel.external_reference == reference,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(rows) == 1
    assert str(rows[0].subscription_id) == subscription_a
    assert rows[0].amount == Decimal("10.0000")


async def test_postgres_usage_key_collision_does_not_cross_subscriptions(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_a = await _create_subscription(client, factory, headers)
    subscription_b = await _create_subscription(client, factory, headers)
    payload = _usage_payload(
        subscription_a,
        idempotency_key=f"collision-{uuid.uuid4().hex}",
    )

    first_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=payload,
    )
    assert first_response.status_code == 201, first_response.text

    collision_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json={**payload, "subscription_id": subscription_b},
    )
    assert collision_response.status_code == 409, collision_response.text

    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(UsageEventModel).where(
                        UsageEventModel.source == "review41",
                        UsageEventModel.idempotency_key == payload["idempotency_key"],
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(rows) == 1
    assert str(rows[0].subscription_id) == subscription_a
    assert rows[0].quantity == Decimal("1.2500")


async def test_postgres_usage_retry_requires_same_payload(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(client, factory, headers)
    payload = _usage_payload(
        subscription_id,
        idempotency_key=f"retry-{uuid.uuid4().hex}",
    )

    first = await client.post(USAGE_EVENTS_PATH, headers=headers, json=payload)
    retry = await client.post(USAGE_EVENTS_PATH, headers=headers, json=payload)
    changed = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json={**payload, "quantity": "8.0000"},
    )

    assert first.status_code == 201, first.text
    assert retry.status_code == 201, retry.text
    assert changed.status_code == 409, changed.text

    async with factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(UsageEventModel)
            .where(UsageEventModel.idempotency_key == payload["idempotency_key"])
        )
        event = (
            await session.execute(
                select(UsageEventModel).where(
                    UsageEventModel.idempotency_key == payload["idempotency_key"]
                )
            )
        ).scalar_one()

    assert count == 1
    assert event.quantity == Decimal("1.2500")


async def test_postgres_concurrent_duplicate_delivery_is_idempotent(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(client, factory, headers)

    reference = f"concurrent-tx-{uuid.uuid4().hex}"
    transaction_payload = _transaction_payload(
        external_reference=reference,
    )
    transaction_responses = await asyncio.gather(
        *(
            client.post(
                f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
                headers=headers,
                json=transaction_payload,
            )
            for _ in range(3)
        )
    )
    assert all(response.status_code == 201 for response in transaction_responses)

    usage_payload = _usage_payload(
        subscription_id,
        idempotency_key=f"concurrent-usage-{uuid.uuid4().hex}",
    )
    usage_responses = await asyncio.gather(
        *(
            client.post(
                USAGE_EVENTS_PATH,
                headers=headers,
                json=usage_payload,
            )
            for _ in range(3)
        )
    )
    assert all(response.status_code == 201 for response in usage_responses)

    async with factory() as session:
        transaction_count = await session.scalar(
            select(func.count())
            .select_from(TransactionModel)
            .where(
                TransactionModel.external_reference == reference,
            )
        )
        usage_count = await session.scalar(
            select(func.count())
            .select_from(UsageEventModel)
            .where(UsageEventModel.idempotency_key == usage_payload["idempotency_key"])
        )

    assert transaction_count == 1
    assert usage_count == 1


@pytest.mark.parametrize(
    ("kind", "field", "value"),
    [
        ("transaction", "source", "x" * 51),
        ("usage", "source", "x" * 51),
        ("transaction", "amount", "-1"),
        ("transaction", "amount", "NaN"),
        ("transaction", "amount", "Infinity"),
        ("transaction", "amount", "100000000000000"),
        ("transaction", "amount", "0.00001"),
        ("transaction", "currency", "123"),
        ("transaction", "currency", "US"),
        ("transaction", "currency", "€UR"),
        ("usage", "quantity", "-1"),
        ("usage", "quantity", "NaN"),
        ("usage", "quantity", "Infinity"),
        ("usage", "quantity", "100000000000000"),
        ("usage", "quantity", "0.00001"),
    ],
)
async def test_postgres_rejects_invalid_ingestion_values(
    postgres_context,
    kind: str,
    field: str,
    value: str,
) -> None:
    client, _ = postgres_context
    headers = await _register_and_login(client)

    if kind == "transaction":
        payload: dict[str, object] = {
            **_transaction_payload(),
            field: value,
        }
        response = await client.post(
            f"{SUBSCRIPTIONS_PATH}/{uuid.uuid4()}/transactions",
            headers=headers,
            json=payload,
        )
    else:
        payload = {
            **_usage_payload(str(uuid.uuid4())),
            field: value,
        }
        response = await client.post(
            USAGE_EVENTS_PATH,
            headers=headers,
            json=payload,
        )

    assert response.status_code == 422, response.text


async def test_postgres_zero_unknown_and_provenance_are_preserved(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(client, factory, headers)

    zero_payload = _usage_payload(
        subscription_id,
        idempotency_key=f"zero-{uuid.uuid4().hex}",
        quantity="0",
    )
    unknown_payload = _usage_payload(
        subscription_id,
        idempotency_key=f"unknown-{uuid.uuid4().hex}",
        quantity="0",
    )
    unknown_payload["quantity"] = None
    unknown_payload["is_unknown"] = True

    zero_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=zero_payload,
    )
    unknown_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=unknown_payload,
    )

    assert zero_response.status_code == 201, zero_response.text
    assert unknown_response.status_code == 201, unknown_response.text

    keys = [
        zero_payload["idempotency_key"],
        unknown_payload["idempotency_key"],
    ]
    async with factory() as session:
        events = (
            (
                await session.execute(
                    select(UsageEventModel).where(UsageEventModel.idempotency_key.in_(keys))
                )
            )
            .scalars()
            .all()
        )

    by_key = {event.idempotency_key: event for event in events}
    measured_zero = by_key[zero_payload["idempotency_key"]]
    unknown = by_key[unknown_payload["idempotency_key"]]

    assert measured_zero.quantity == Decimal("0.0000")
    assert measured_zero.is_unknown is False
    assert unknown.quantity is None
    assert unknown.is_unknown is True

    evidence = measured_zero.evidence_json
    assert evidence["source"] == "review41"
    assert evidence["ingestion_method"] == "api"
    assert evidence["idempotency_key"] == zero_payload["idempotency_key"]
    ingestion_time = datetime.fromisoformat(evidence["ingested_at"])
    assert ingestion_time.utcoffset() is not None


async def test_postgres_different_users_can_use_same_keys(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers_a = await _register_and_login(client)
    headers_b = await _register_and_login(client)
    subscription_a = await _create_subscription(client, factory, headers_a)
    subscription_b = await _create_subscription(client, factory, headers_b)

    reference = f"shared-{uuid.uuid4().hex}"
    tx_payload = _transaction_payload(external_reference=reference)

    tx_a = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_a}/transactions",
        headers=headers_a,
        json=tx_payload,
    )
    tx_b = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_b}/transactions",
        headers=headers_b,
        json=tx_payload,
    )
    assert tx_a.status_code == 201, tx_a.text
    assert tx_b.status_code == 201, tx_b.text

    usage_key = f"shared-{uuid.uuid4().hex}"
    usage_a = _usage_payload(subscription_a, idempotency_key=usage_key)
    usage_b = {**usage_a, "subscription_id": subscription_b}

    event_a = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers_a,
        json=usage_a,
    )
    event_b = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers_b,
        json=usage_b,
    )
    assert event_a.status_code == 201, event_a.text
    assert event_b.status_code == 201, event_b.text

    async with factory() as session:
        tx_count = await session.scalar(
            select(func.count())
            .select_from(TransactionModel)
            .where(TransactionModel.external_reference == reference)
        )
        event_count = await session.scalar(
            select(func.count())
            .select_from(UsageEventModel)
            .where(UsageEventModel.idempotency_key == usage_key)
        )

    assert tx_count == 2
    assert event_count == 2


async def test_postgres_ingestion_requires_authentication(
    postgres_context,
) -> None:
    client, _ = postgres_context
    subscription_id = str(uuid.uuid4())

    transaction_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
        json=_transaction_payload(),
    )
    usage_response = await client.post(
        USAGE_EVENTS_PATH,
        json=_usage_payload(subscription_id),
    )

    assert transaction_response.status_code == 401
    assert usage_response.status_code == 401


async def test_postgres_soft_deleted_subscription_rejects_ingestion(
    postgres_context,
) -> None:
    client, factory = postgres_context
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(client, factory, headers)

    async with factory() as session:
        await session.execute(
            update(SubscriptionModel)
            .where(SubscriptionModel.id == uuid.UUID(subscription_id))
            .values(deleted_at=datetime.now(UTC))
        )
        await session.commit()

    transaction_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
        headers=headers,
        json=_transaction_payload(),
    )
    usage_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=_usage_payload(subscription_id),
    )

    assert transaction_response.status_code == 404
    assert usage_response.status_code == 404
