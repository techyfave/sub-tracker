from __future__ import annotations

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AuditEventModel, ConsentModel

BASE = "/api/v1/consents"


async def _token(client: AsyncClient, email: str) -> str:
    registered = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correct-horse"}
    )
    assert registered.status_code == 201, registered.text
    logged_in = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse"}
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()["tokens"]["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_consent_grant_list_revoke_and_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _token(client, "consent@example.com")
    headers = _headers(token)
    granted = await client.post(
        BASE,
        headers=headers,
        json={"policy_version": "2026-10", "scopes": ["subscriptions.read", "analytics.use"]},
    )
    assert granted.status_code == 201, granted.text
    body = granted.json()
    assert body["policy_version"] == "2026-10"
    assert body["scopes"] == ["subscriptions.read", "analytics.use"]
    assert body["granted_at"]
    assert body["revoked_at"] is None

    listed = await client.get(BASE, headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [body["id"]]

    revoked = await client.delete(f"{BASE}/{body['id']}", headers=headers)
    assert revoked.status_code == 200, revoked.text
    first_revoked_at = revoked.json()["revoked_at"]
    assert first_revoked_at

    repeated = await client.delete(f"{BASE}/{body['id']}", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["revoked_at"] == first_revoked_at

    events: list[AuditEventModel] = list((await db_session.scalars(select(AuditEventModel))).all())
    assert len(events) == 1
    assert events[0].event_type == "consent.revoked"
    assert str(events[0].resource_id) == revoked.json()["id"]
    record = await db_session.get(ConsentModel, UUID(body["id"]))
    assert record is not None
    assert record.revoked_at is not None


async def test_consent_endpoints_require_authentication(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401
    assert (
        await client.post(BASE, json={"policy_version": "v1", "scopes": ["profile.read"]})
    ).status_code == 401
    assert (await client.delete(f"{BASE}/00000000-0000-0000-0000-000000000000")).status_code == 401


async def test_invalid_consent_payload_is_rejected(client: AsyncClient) -> None:
    token = await _token(client, "invalid-consent@example.com")
    headers = _headers(token)
    invalid_payloads = [
        {"policy_version": "", "scopes": ["profile.read"]},
        {"policy_version": "v1", "scopes": []},
        {"policy_version": "v1", "scopes": ["bad scope"]},
        {"policy_version": "v1", "scopes": ["profile.read", "profile.read"]},
        {"policy_version": "v1", "scopes": ["profile.read"], "user_id": "someone-else"},
    ]
    for payload in invalid_payloads:
        response = await client.post(BASE, headers=headers, json=payload)
        assert response.status_code == 422, (payload, response.text)


async def test_users_cannot_revoke_another_users_consent(client: AsyncClient) -> None:
    owner_token = await _token(client, "owner@example.com")
    other_token = await _token(client, "other@example.com")
    created = await client.post(
        BASE,
        headers=_headers(owner_token),
        json={"policy_version": "v1", "scopes": ["profile.read"]},
    )
    assert created.status_code == 201
    denied = await client.delete(f"{BASE}/{created.json()['id']}", headers=_headers(other_token))
    assert denied.status_code == 403
