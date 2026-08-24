from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_reports_unavailable_database(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable() -> bool:
        return False

    from app.api.v1.endpoints import health

    monkeypatch.setattr(health, "database_is_ready", unavailable)
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


async def test_readiness_reports_available_database(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def available() -> bool:
        return True

    from app.api.v1.endpoints import health

    monkeypatch.setattr(health, "database_is_ready", available)
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
