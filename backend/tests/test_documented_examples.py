"""Ensure the contributor examples remain usable public contracts."""

import pytest

from app.api.recommendation_examples import RECOMMENDATION_EXAMPLE
from app.api.v1.schemas.recommendation import RecommendationResponse
from app.api.v1.schemas.subscriptions import TransactionCreate, UsageEventCreate
from app.main import app
from check_openapi import main


def test_documentation_inventory_and_examples(capsys):
    main()
    assert "OPENAPI SCHEMA AUDIT PASSED" in capsys.readouterr().out
    RecommendationResponse.model_validate(RECOMMENDATION_EXAMPLE)
    for model in (TransactionCreate, UsageEventCreate):
        for example in model.model_json_schema()["examples"]:
            model.model_validate(example)


def test_documented_missing_source_validation():
    # Validate the model directly; HTTP tests already exercise authenticated ingestion.
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        UsageEventCreate.model_validate(
            {
                "subscription_id": "40000000-0000-4000-8000-000000000001",
                "occurrence_time": "2026-10-01T10:00:00Z",
                "is_unknown": True,
            }
        )
    assert any(error["loc"] == ("source",) for error in exc.value.errors())


def test_refresh_does_not_advertise_unimplemented_rate_limit():
    assert "429" not in app.openapi()["paths"]["/api/v1/auth/refresh"]["post"]["responses"]


@pytest.mark.parametrize("field", ["request", "success", "authorization"])
def test_audit_rejects_missing_required_examples(monkeypatch, capsys, field):
    from copy import deepcopy

    schema = deepcopy(app.openapi())
    if field == "request":
        op = schema["paths"]["/api/v1/subscriptions/usage-events"]["post"]
        op["requestBody"]["content"]["application/json"] = {"schema": {}}
    else:
        op = schema["paths"]["/api/v1/recommendations"]["get"]
        if field == "success":
            op["responses"]["200"]["content"]["application/json"] = {"schema": {}}
        else:
            del op["responses"]["401"]
    monkeypatch.setattr(app, "openapi", lambda: schema)
    with pytest.raises(SystemExit):
        main()
    assert "OPENAPI AUDIT FAILED" in capsys.readouterr().out
