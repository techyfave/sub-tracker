import pytest  # error checking in tests

from app.api.v1.schemas.recommendation import (  # code under test
    AnalysisStatus,  # public analysis states
    public_snapshot,  # evidence projection
    public_uncertainty,  # uncertainty projection
    to_public_status,  # stored -> public
    to_stored_status,  # public -> stored
)
from app.infrastructure.database.models import WorkStatus  # stored statuses
from app.infrastructure.database.repositories.recommendation_read_repository import (
    UNPUBLISHED_ANALYSIS_STATUSES,  # stored states that are not published
)


def test_every_stored_status_is_mapped_or_explicitly_unpublished() -> None:
    # fails if #13 adds a stored status that is neither mapped nor listed as unpublished
    for member in WorkStatus:
        # explicitly unpublished states have no public word by design
        if member in UNPUBLISHED_ANALYSIS_STATUSES:
            continue
        # every other stored value must convert to a public state and back unchanged
        assert to_stored_status(to_public_status(member.value)) == member.value


def test_unpublished_states_have_no_public_mapping() -> None:
    # cancelled is not part of the documented analysis states
    assert WorkStatus.CANCELLED in UNPUBLISHED_ANALYSIS_STATUSES
    # asking for its public word is an error, so nothing can publish it by accident
    with pytest.raises(KeyError):
        to_public_status("cancelled")


def test_succeeded_is_published_as_completed() -> None:
    # the job word becomes the analysis word
    assert to_public_status("succeeded") == AnalysisStatus.COMPLETED
    # the public vocabulary is exactly the documented one
    assert {state.value for state in AnalysisStatus} == {
        "queued",
        "running",
        "completed",
        "failed",
    }


def test_snapshot_projection_drops_unknown_nested_and_unsafe_values() -> None:
    # stored JSON mixing public values with internal and unsafe ones
    raw = {
        "sessions": 4,  # public number
        "value_signal": "low",  # public token
        "conflict": True,  # public boolean
        "provider_api_key": "x-secret",  # key not on the allowlist
        "metadata": {"access_token": "t"},  # nested object
        "reason": {"token": "t"},  # allowed key, but a nested value
        "supports": "free text with spaces!",  # allowed key, but not a simple token
    }
    # only the safe, allowlisted values survive
    assert public_snapshot(raw) == {"sessions": 4, "value_signal": "low", "conflict": True}


def test_uncertainty_projection_keeps_only_level_and_reason() -> None:
    # internal keys are removed
    raw = {"level": "high", "reason": "missing_usage", "model_trace": "p", "provider_api_key": "k"}
    assert public_uncertainty(raw) == {"level": "high", "reason": "missing_usage"}
    # unsafe or nested values become null instead of leaking
    assert public_uncertainty({"level": {"nested": "x"}}) == {"level": None, "reason": None}


@pytest.mark.parametrize(
    "key,value",
    [
        ("amount", "NaN"),
        ("amount", "1e10"),
        ("amount", -1),
        ("amount", True),
        ("amount", "-1.00"),
        ("amount", "1.00001"),
        ("amount", "100000000000000.00"),
        ("currency", "private-provider-secret"),
        ("currency", {"access_token": "secret"}),
        ("quantity", ["secret"]),
        ("quantity", 1.5),
        ("quantity", "Infinity"),
        ("kind", "private model trace with spaces"),
        ("is_unknown", "true"),
        ("is_unknown", 1),
        ("billing_interval", "secret"),
        ("occurred_at", "secret"),
        ("occurred_at", "2026-01-01T12:00:00"),
        ("occurred_at", "2026-99-99T12:00:00+00:00"),
    ],
)
def test_typed_snapshot_fields_reject_invalid_values(key, value):
    assert public_snapshot({key: value}) == {}


def test_typed_snapshot_fields_preserve_precision_and_unknown_usage():
    raw = {
        "amount": "120.0700",
        "currency": "NGN",
        "quantity": None,
        "is_unknown": True,
        "kind": "session",
        "billing_interval": "yearly",
        "occurred_at": "2026-01-01T12:00:00.123456+00:00",
    }
    assert public_snapshot(raw) == raw
    assert public_snapshot({"quantity": "0.0000", "is_unknown": False}) == {
        "quantity": "0.0000",
        "is_unknown": False,
    }


@pytest.mark.parametrize(
    "key",
    [
        "amount",
        "currency",
        "quantity",
        "is_unknown",
        "kind",
        "billing_interval",
        "occurred_at",
    ],
)
def test_typed_snapshot_fields_never_publish_nested_data(key):
    assert public_snapshot({key: {"model_trace": "secret"}}) == {}


@pytest.mark.parametrize("value", ["2.0", "1", 1, True, {"model_trace": "secret"}])
def test_target_schema_version_requires_supported_literal(value):
    assert public_snapshot({"target_schema_version": value}) == {}


def test_target_schema_version_is_public():
    assert public_snapshot({"target_schema_version": "1.0"}) == {"target_schema_version": "1.0"}
