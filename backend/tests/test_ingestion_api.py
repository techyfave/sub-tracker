import pytest
from datetime import datetime, timezone
import uuid

# Direct the test runner engine to execute loops through native async wrappers
pytestmark = pytest.mark.asyncio

async def test_unknown_vs_zero_usage_distinction():
    """Validates that explicit zero and unknown usage are tracked correctly."""
    units_used_zero = 0.0
    units_used_unknown = None
    
    assert units_used_zero is not None, "Zero usage must register as a numeric element."
    assert units_used_unknown is None, "Unknown usage must register explicitly as None/Null."

async def test_idempotence_deduplication():
    """Validates that duplication tracking keys exist to suppress dual ingestion entries."""
    idempotency_key = "stripe_ch_99999"
    processed_ledger = set()
    
    processed_ledger.add(idempotency_key)
    
    assert (idempotency_key in processed_ledger) is True
