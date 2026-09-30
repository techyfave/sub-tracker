from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.core import PlanModel

REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
SUBSCRIPTIONS_PATH = "/api/v1/subscriptions"


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "correct-horse",
) -> str:
    register_response = await client.post(
        REGISTER_PATH,
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        LOGIN_PATH,
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200, login_response.text

    return login_response.json()["tokens"]["access_token"]


async def _create_plan(
    db_session: AsyncSession,
) -> PlanModel:
    provider_id = uuid4()

    # The provider must exist because plans.provider_id is a foreign key.
    from app.infrastructure.database.models.core import ProviderModel

    provider = ProviderModel(
        id=provider_id,
        slug=f"test-provider-{uuid4().hex[:8]}",
        display_name="Test Provider",
    )

    db_session.add(provider)
    await db_session.flush()

    plan = PlanModel(
        id=uuid4(),
        provider_id=provider.id,
        external_reference=f"plan-{uuid4().hex[:8]}",
        name="Test Monthly Plan",
        amount=Decimal("5000.00"),
        currency="NGN",
        billing_interval="monthly",
    )

    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    return plan


async def test_create_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _register_and_login(
        client,
        email="subscriber@example.com",
    )

    plan = await _create_plan(db_session)

    response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Netflix",
        },
    )

    assert response.status_code == 201, response.text

    body = response.json()

    assert body["plan_id"] == str(plan.id)
    assert body["name"] == "Netflix"
    assert body["status"] == "active"
    assert body["provider_connection_id"] is None
    assert body["deleted_at"] is None


async def test_list_subscriptions_returns_users_subscriptions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _register_and_login(
        client,
        email="list@example.com",
    )

    plan = await _create_plan(db_session)

    create_response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Netflix",
        },
    )

    assert create_response.status_code == 201, create_response.text

    response = await client.get(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["pagination"]["total_items"] == 1
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 20
    assert body["pagination"]["total_pages"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Netflix"


async def test_get_subscription_returns_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _register_and_login(
        client,
        email="get@example.com",
    )

    plan = await _create_plan(db_session)

    create_response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Spotify",
        },
    )

    assert create_response.status_code == 201, create_response.text

    subscription_id = create_response.json()["id"]

    response = await client.get(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == subscription_id
    assert response.json()["name"] == "Spotify"


async def test_update_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _register_and_login(
        client,
        email="update@example.com",
    )

    plan = await _create_plan(db_session)

    create_response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Netflix",
        },
    )

    assert create_response.status_code == 201, create_response.text

    subscription_id = create_response.json()["id"]

    response = await client.patch(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Netflix Premium",
            "status": "paused",
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["id"] == subscription_id
    assert body["name"] == "Netflix Premium"
    assert body["status"] == "paused"


async def test_delete_subscription_soft_deletes_it(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _register_and_login(
        client,
        email="delete@example.com",
    )

    plan = await _create_plan(db_session)

    create_response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Disney Plus",
        },
    )

    assert create_response.status_code == 201, create_response.text

    subscription_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 204

    get_response = await client.get(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 404

    list_response = await client.get(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["pagination"]["total_items"] == 0


async def test_subscription_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get(SUBSCRIPTIONS_PATH)

    assert response.status_code == 401


async def test_user_cannot_access_another_users_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_token = await _register_and_login(
        client,
        email="owner@example.com",
    )

    other_user_token = await _register_and_login(
        client,
        email="other@example.com",
    )

    plan = await _create_plan(db_session)

    create_response = await client.post(
        SUBSCRIPTIONS_PATH,
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "plan_id": str(plan.id),
            "name": "Netflix",
        },
    )

    assert create_response.status_code == 201, create_response.text

    subscription_id = create_response.json()["id"]

    response = await client.get(
        f"{SUBSCRIPTIONS_PATH}/{subscription_id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
    )

    assert response.status_code == 404
