from __future__ import annotations

from httpx import AsyncClient


async def test_validation_error_uses_problem_details(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )

    body = response.json()

    assert body["type"].endswith("/validation-error")
    assert body["title"] == "Validation Error"
    assert body["status"] == 422
    assert body["detail"] == "The request contains invalid data."
    assert body["instance"] == "/api/v1/auth/register"

    assert "errors" in body
    assert len(body["errors"]) >= 1