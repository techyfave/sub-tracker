from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.core import (
    ProviderModel,
    TransactionModel,
    UsageEventModel,
)

pytestmark = pytest.mark.asyncio

REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
SUBSCRIPTIONS_PATH = "/api/v1/subscriptions"
USAGE_EVENTS_PATH = f"{SUBSCRIPTIONS_PATH}/usage-events"


async def _register_and_login(
    client: AsyncClient,
) -> dict[str, str]:
    """Create a unique test user and return its bearer authorization header."""
    email = f"ingestion-{uuid.uuid4().hex}@example.com"
    password = "correct-horse-test-password"

    register_response = await client.post(
        REGISTER_PATH,
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        LOGIN_PATH,
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict[str, str],
) -> str:
    """Create a provider and an owned subscription for ingestion tests."""
    provider = ProviderModel(
        slug=f"ingestion-{uuid.uuid4().hex}",
        display_name="Ingestion Test Provider",
    )
    db_session.add(provider)
    await db_session.commit()

    response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers=headers,
        json={
            "name": "Ingestion Test Subscription",
            "plan": {
                "provider_id": str(provider.id),
                "name": "Test Monthly Plan",
                "amount": "9.99",
                "currency": "USD",
                "billing_interval": "monthly",
            },
        },
    )
    assert response.status_code == 201, response.text

    subscription_id = response.json()["id"]
    assert subscription_id
    return str(subscription_id)


def _transaction_payload(
    *,
    amount: str = "49.99",
    external_reference: str = "tx-test-001",
) -> dict[str, str]:
    return {
        "amount": amount,
        "currency": "USD",
        "occurrence_time": datetime.now(UTC).isoformat(),
        "source": "stripe",
        "external_reference": external_reference,
    }


def _usage_payload(
    subscription_id: str,
    *,
    idempotency_key: str | None = "usage-test-001",
    quantity: str = "12.50",
) -> dict[str, object]:
    return {
        "subscription_id": subscription_id,
        "occurrence_time": datetime.now(UTC).isoformat(),
        "quantity": quantity,
        "is_unknown": False,
        "source": "datadog",
        "idempotency_key": idempotency_key,
    }


async def test_transaction_duplicate_updates_existing_record(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """The same transaction reference must not create a second record."""
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(
        client,
        db_session,
        headers,
    )

    first_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
        headers=headers,
        json=_transaction_payload(amount="49.99"),
    )
    assert first_response.status_code == 201, first_response.text

    second_response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
        headers=headers,
        json=_transaction_payload(amount="59.99"),
    )
    assert second_response.status_code == 201, second_response.text

    result = await db_session.execute(
        select(TransactionModel).where(
            TransactionModel.external_reference == "tx-test-001",
            TransactionModel.source == "stripe",
        )
    )
    transactions = result.scalars().all()

    assert len(transactions) == 1
    assert transactions[0].amount == Decimal("59.9900")


async def test_usage_event_duplicate_key_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Exact retries succeed; reusing a key with changed data conflicts."""
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(
        client,
        db_session,
        headers,
    )

    payload = _usage_payload(
        subscription_id,
        idempotency_key="usage-duplicate-001",
        quantity="12.50",
    )

    first_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=payload,
    )
    assert first_response.status_code == 201, first_response.text

    replay_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=payload,
    )
    assert replay_response.status_code == 201, replay_response.text

    changed_response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json={**payload, "quantity": "15.00"},
    )
    assert changed_response.status_code == 409, changed_response.text

    events = (
        (
            await db_session.execute(
                select(UsageEventModel).where(
                    UsageEventModel.source == "datadog",
                    UsageEventModel.idempotency_key == "usage-duplicate-001",
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(events) == 1
    assert events[0].quantity == Decimal("12.5000")


async def test_usage_events_without_key_can_be_recorded_separately(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Omitting the optional key allows separate events from the same source."""
    headers = await _register_and_login(client)
    subscription_id = await _create_subscription(
        client,
        db_session,
        headers,
    )

    for quantity in ("2.00", "3.00"):
        response = await client.post(
            USAGE_EVENTS_PATH,
            headers=headers,
            json=_usage_payload(
                subscription_id,
                idempotency_key=None,
                quantity=quantity,
            ),
        )
        assert response.status_code == 201, response.text

    count = await db_session.scalar(
        select(func.count())
        .select_from(UsageEventModel)
        .where(
            UsageEventModel.source == "datadog",
            UsageEventModel.idempotency_key.is_(None),
        )
    )

    assert count == 2


async def test_transaction_cannot_target_another_users_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A user must not be able to ingest transactions for another user."""
    owner_headers = await _register_and_login(client)
    subscription_id = await _create_subscription(
        client,
        db_session,
        owner_headers,
    )
    other_user_headers = await _register_and_login(client)

    response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}/transactions",
        headers=other_user_headers,
        json=_transaction_payload(),
    )

    assert response.status_code == 404


async def test_usage_event_cannot_target_another_users_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A user must not be able to ingest usage for another user's subscription."""
    owner_headers = await _register_and_login(client)
    subscription_id = await _create_subscription(
        client,
        db_session,
        owner_headers,
    )
    other_user_headers = await _register_and_login(client)

    response = await client.post(
        USAGE_EVENTS_PATH,
        headers=other_user_headers,
        json=_usage_payload(subscription_id),
    )

    assert response.status_code == 404


async def test_ingest_transaction_rejects_unknown_subscription(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(client)
    payload = _transaction_payload()

    response = await client.post(
        f"{SUBSCRIPTIONS_PATH}/{uuid.uuid4()}/transactions",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 404


async def test_ingest_usage_rejects_contradictory_input(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(client)
    payload = {
        "subscription_id": str(uuid.uuid4()),
        "occurrence_time": datetime.now(UTC).isoformat(),
        "quantity": "12.50",
        "is_unknown": True,
        "source": "datadog",
    }

    response = await client.post(
        USAGE_EVENTS_PATH,
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422
