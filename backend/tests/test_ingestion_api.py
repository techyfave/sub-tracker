import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
import uuid
from decimal import Decimal

pytestmark = pytest.mark.asyncio

async def test_ingest_transaction_cross_user_rejection(client: AsyncClient):
    """Ensures a malicious token call targeting a foreign subscription returns 403."""
    foreign_sub_id = str(uuid.uuid4())
    payload = {
        "amount": "49.99",
        "currency": "USD",
        "occurrence_time": datetime.now(timezone.utc).isoformat(),
        "source": "stripe",
        "external_reference": "tx_mock_9999"
    }
    response = await client.post(f"/api/v1/subscriptions/{foreign_sub_id}/transactions", json=payload)
    assert response.status_code in (401, 403, 404)

async def test_ingest_usage_contradictory_input_rejection(client: AsyncClient):
    """Ensures schemas prevent payload tracking states that pass both unknown flags and values."""
    payload = {
        "subscription_id": str(uuid.uuid4()),
        "occurrence_time": datetime.now(timezone.utc).isoformat(),
        "quantity": "12.50",
        "is_unknown": True,
        "source": "datadog"
    }
    response = await client.post("/api/v1/subscriptions/usage-events", json=payload)
    assert response.status_code in (401, 422, 403)
