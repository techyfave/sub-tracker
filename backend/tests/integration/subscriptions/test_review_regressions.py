from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.core import (
    PlanModel,
    ProviderConnectionModel,
    ProviderModel,
    SubscriptionModel,
    TransactionModel,
    UsageEventModel,
)

PATH = "/api/v1/subscriptions"


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "correct-horse"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    response = await client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": "Bearer " + response.json()["tokens"]["access_token"]}


async def plan_input(session: AsyncSession) -> dict[str, str]:
    provider = ProviderModel(id=uuid4(), slug=str(uuid4()), display_name="Manual provider")
    session.add(provider)
    await session.commit()
    return {
        "provider_id": str(provider.id),
        "name": "Monthly",
        "amount": "19.1234",
        "currency": "usd",
        "billing_interval": "monthly",
    }


async def test_plans_round_trip_and_copy_on_write(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await login(client, "plans@example.com")
    plan = await plan_input(db_session)
    response = await client.post(
        PATH,
        headers=headers,
        json={
            "name": "Service",
            "plan": plan,
            "plan_alternatives": [{**plan, "amount": "10.0001"}],
            "renewal_at": "2026-11-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    original_id = UUID(body["plan_id"])
    assert Decimal(body["plan"]["amount"]) == Decimal("19.1234")
    assert body["plan"]["currency"] == "USD"
    assert Decimal(body["plan_alternatives"][0]["amount"]) == Decimal("10.0001")
    url = PATH + "/" + body["id"]
    assert (await client.get(url, headers=headers)).json()["plan"] == body["plan"]
    response = await client.patch(
        url,
        headers=headers,
        json={"plan": {**plan, "amount": "15.4321"}, "plan_alternatives": [], "renewal_at": None},
    )
    assert response.status_code == 200, response.text
    assert response.json()["plan_id"] != str(original_id)
    assert response.json()["plan_alternatives"] == []
    assert response.json()["renewal_at"] is None
    original = await db_session.get(PlanModel, original_id)
    assert original is not None and original.amount == Decimal("19.1234")
    stored = await db_session.get(PlanModel, UUID(response.json()["plan_id"]))
    assert stored is not None and stored.amount == Decimal("15.4321")


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", "-1"),
        ("amount", "NaN"),
        ("amount", "Infinity"),
        ("amount", "0.00001"),
        ("amount", "100000000000000"),
        ("currency", "123"),
        ("currency", "US"),
        ("currency", "Ã¢â€šÂ¬UR"),
        ("billing_interval", "sometimes"),
    ],
)
async def test_invalid_plan_money(
    client: AsyncClient, db_session: AsyncSession, field: str, value: str
) -> None:
    headers = await login(client, "invalid@example.com")
    plan = await plan_input(db_session)
    plan[field] = value
    for payload in (
        {"name": "Bad", "plan": plan},
        {
            "name": "Bad",
            "plan": {**plan, "amount": "1", "currency": "USD", "billing_interval": "monthly"},
            "plan_alternatives": [plan],
        },
    ):
        response = await client.post(PATH, headers=headers, json=payload)
        assert response.status_code == 422, response.text
    assert await db_session.scalar(select(func.count()).select_from(PlanModel)) == 0


async def test_ownership_lifecycle_pagination_and_history(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await login(client, "owner-review@example.com")
    other = await login(client, "other-review@example.com")
    plan = await plan_input(db_session)
    created = await client.post(PATH, headers=owner, json={"name": "Service", "plan": plan})
    assert created.status_code == 201, created.text
    body = created.json()
    url = PATH + "/" + body["id"]
    for method in ("get", "patch", "delete"):
        response = await client.request(
            method,
            url,
            headers=other,
            **({"json": {"name": "Stolen"}} if method == "patch" else {}),
        )
        assert response.status_code == 404
    assert (await client.get(PATH, headers=other)).json()["items"] == []
    for state in ("paused", "active", "cancelled"):
        response = await client.patch(url, headers=owner, json={"status": state})
        assert response.status_code == 200, response.text
    assert (await client.patch(url, headers=owner, json={"status": "paused"})).status_code == 400
    assert (await client.patch(url, headers=owner, json={"status": "invalid"})).status_code == 422
    assert (await client.patch(url, headers=owner, json={"name": None})).status_code == 422
    assert (
        await client.patch(url, headers=owner, json={"renewal_at": "2026-11-01"})
    ).status_code == 422
    listing = await client.get(PATH + "?status=cancelled&page_size=1", headers=owner)
    assert listing.json()["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total_items": 1,
        "total_pages": 1,
    }
    assert (await client.get(PATH + "?status=active", headers=owner)).json()["items"] == []
    assert (await client.get(PATH + "?page=2&page_size=1", headers=owner)).json()["items"] == []
    subscription_id, user_id = UUID(body["id"]), UUID(body["user_id"])
    transaction = TransactionModel(
        id=uuid4(),
        user_id=user_id,
        subscription_id=subscription_id,
        amount=Decimal("19.1234"),
        currency="USD",
        occurred_at=datetime.now(UTC),
        source="manual",
    )
    usage = UsageEventModel(
        id=uuid4(),
        user_id=user_id,
        subscription_id=subscription_id,
        occurred_at=datetime.now(UTC),
        source="manual",
        kind="visit",
        is_unknown=False,
    )
    db_session.add_all([transaction, usage])
    await db_session.commit()
    assert (await client.delete(url, headers=owner)).status_code == 204
    assert (await client.get(url, headers=owner)).status_code == 404
    assert (await client.patch(url, headers=owner, json={"name": "restore"})).status_code == 404
    assert (await client.delete(url, headers=owner)).status_code == 404
    assert (await client.get(PATH, headers=owner)).json()["items"] == []
    transaction_id, usage_id = transaction.id, usage.id
    db_session.expire_all()
    assert await db_session.get(TransactionModel, transaction_id) is not None
    assert await db_session.get(UsageEventModel, usage_id) is not None
    stored = await db_session.get(SubscriptionModel, subscription_id)
    assert stored is not None and stored.deleted_at is not None


async def test_references_are_validated(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await login(client, "refs@example.com")
    other = await login(client, "refs-other@example.com")
    plan = await plan_input(db_session)
    other_user = (await client.get("/api/v1/me", headers=other)).json()
    connection = ProviderConnectionModel(
        id=uuid4(),
        user_id=UUID(other_user["id"]),
        provider_id=UUID(plan["provider_id"]),
        external_reference="private",
        status="active",
    )
    db_session.add(connection)
    await db_session.commit()
    for payload in (
        {"plan_id": str(uuid4())},
        {"plan": {**plan, "provider_id": str(uuid4())}},
        {"plan": plan, "provider_connection_id": str(connection.id)},
    ):
        response = await client.post(PATH, headers=owner, json={"name": "Invalid", **payload})
        assert response.status_code == 422, response.text
    assert await db_session.scalar(select(func.count()).select_from(PlanModel)) == 0
    created = await client.post(PATH, headers=owner, json={"name": "Valid", "plan": plan})
    url = PATH + "/" + created.json()["id"]
    for payload in ({"plan_id": str(uuid4())}, {"provider_connection_id": str(connection.id)}):
        assert (await client.patch(url, headers=owner, json=payload)).status_code == 422
    assert (await client.get(url, headers=owner)).json()["provider_connection_id"] is None


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", PATH, None),
        ("post", PATH, {"name": "x", "plan_id": str(uuid4())}),
        ("get", PATH + "/" + str(uuid4()), None),
        ("patch", PATH + "/" + str(uuid4()), {"name": "x"}),
        ("delete", PATH + "/" + str(uuid4()), None),
    ],
)
async def test_all_routes_require_auth(
    client: AsyncClient, method: str, path: str, payload: dict[str, str] | None
) -> None:
    assert (await client.request(method, path, json=payload)).status_code == 401
