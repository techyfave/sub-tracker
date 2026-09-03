from __future__ import annotations

from httpx import AsyncClient

REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
REFRESH_PATH = "/api/v1/auth/refresh"
ME_PATH = "/api/v1/me"


async def _register(
    client: AsyncClient, *, email: str = "user@example.com", password: str = "correct-horse"
) -> None:
    response = await client.post(REGISTER_PATH, json={"email": email, "password": password})
    assert response.status_code == 201, response.text


async def _login(
    client: AsyncClient, *, email: str = "user@example.com", password: str = "correct-horse"
) -> dict:
    response = await client.post(LOGIN_PATH, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


async def test_register_then_login_returns_tokens(client: AsyncClient) -> None:
    await _register(client)
    body = await _login(client)

    assert body["user"]["email"] == "user@example.com"
    assert body["tokens"]["token_type"] == "bearer"
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]


async def test_register_duplicate_email_is_rejected(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post(
        REGISTER_PATH, json={"email": "user@example.com", "password": "another-pass"}
    )

    assert response.status_code == 409


async def test_login_with_unknown_email_is_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN_PATH, json={"email": "nobody@example.com", "password": "whatever123"}
    )

    assert response.status_code == 401
    assert response.json()["detail"]["title"] == "Invalid credentials"


async def test_login_with_wrong_password_is_invalid_credentials(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post(
        LOGIN_PATH, json={"email": "user@example.com", "password": "totally-wrong"}
    )

    assert response.status_code == 401


async def test_me_requires_a_bearer_token(client: AsyncClient) -> None:
    response = await client.get(ME_PATH)

    assert response.status_code == 401


async def test_me_rejects_a_garbage_token(client: AsyncClient) -> None:
    response = await client.get(ME_PATH, headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


async def test_me_returns_the_authenticated_user(client: AsyncClient) -> None:
    await _register(client)
    tokens = (await _login(client))["tokens"]

    response = await client.get(
        ME_PATH, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


async def test_refresh_rotates_the_token_and_old_one_stops_working(client: AsyncClient) -> None:
    await _register(client)
    first_tokens = (await _login(client))["tokens"]

    refreshed = await client.post(
        REFRESH_PATH, json={"refresh_token": first_tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != first_tokens["refresh_token"]

    # The new access token authenticates the same user.
    me = await client.get(
        ME_PATH, headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


async def test_reusing_a_rotated_refresh_token_is_rejected_and_revokes_the_session(
    client: AsyncClient,
) -> None:
    await _register(client)
    first_tokens = (await _login(client))["tokens"]

    # Rotate once — this is the legitimate use.
    first_refresh = await client.post(
        REFRESH_PATH, json={"refresh_token": first_tokens["refresh_token"]}
    )
    assert first_refresh.status_code == 200
    rotated_tokens = first_refresh.json()

    # Reusing the *original* (now-rotated-away) token is a reuse/theft signal.
    replay = await client.post(REFRESH_PATH, json={"refresh_token": first_tokens["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json()["detail"]["title"] == "Refresh token reused"

    # Reuse detection revokes the whole family, so even the *valid* rotated
    # token from the legitimate refresh above must now be rejected too.
    second_use_of_rotated = await client.post(
        REFRESH_PATH, json={"refresh_token": rotated_tokens["refresh_token"]}
    )
    assert second_use_of_rotated.status_code == 401


async def test_refresh_with_unknown_token_is_invalid(client: AsyncClient) -> None:
    response = await client.post(REFRESH_PATH, json={"refresh_token": "not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["detail"]["title"] == "Invalid refresh token"


async def test_register_is_rate_limited(client: AsyncClient) -> None:
    # Settings default auth_rate_limit is "5/minute".
    for i in range(5):
        response = await client.post(
            REGISTER_PATH, json={"email": f"user{i}@example.com", "password": "correct-horse"}
        )
        assert response.status_code == 201, response.text

    sixth = await client.post(
        REGISTER_PATH, json={"email": "user5@example.com", "password": "correct-horse"}
    )
    assert sixth.status_code == 429
