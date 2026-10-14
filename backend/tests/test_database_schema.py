from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Numeric

from app.infrastructure.database import models
from app.infrastructure.database.base import Base
from app.infrastructure.database.repositories import (
    AuditEventRepository,
    RecommendationRepository,
)

REQUIRED_TABLES = {
    "actions",
    "analyses",
    "audit_events",
    "consents",
    "conversations",
    "evaluation_results",
    "evaluation_runs",
    "messages",
    "plans",
    "prompt_versions",
    "provider_connections",
    "providers",
    "recommendation_decisions",
    "recommendation_evidence",
    "recommendations",
    "refresh_tokens",
    "savings_records",
    "subscription_alternatives",
    "subscriptions",
    "transactions",
    "usage_events",
    "users",
}

USER_OWNED_TABLES = {
    "actions",
    "analyses",
    "audit_events",
    "consents",
    "conversations",
    "messages",
    "provider_connections",
    "recommendation_decisions",
    "recommendation_evidence",
    "recommendations",
    "savings_records",
    "subscriptions",
    "transactions",
    "usage_events",
}


def test_metadata_contains_every_mvp_table() -> None:
    assert set(Base.metadata.tables) == REQUIRED_TABLES


def test_every_user_owned_table_has_an_indexed_user_id() -> None:
    for table_name in USER_OWNED_TABLES:
        table = Base.metadata.tables[table_name]
        assert "user_id" in table.columns, table_name
        assert table.columns.user_id.index, table_name


def test_money_columns_use_fixed_precision_decimal_and_currency() -> None:
    for table_name, amount_name in (
        ("plans", "amount"),
        ("transactions", "amount"),
        ("recommendations", "monthly_savings_amount"),
        ("recommendations", "annual_savings_amount"),
        ("savings_records", "amount"),
    ):
        table = Base.metadata.tables[table_name]
        amount = table.columns[amount_name]
        currency = table.columns.currency
        assert isinstance(amount.type, Numeric)
        assert amount.type.python_type is Decimal
        assert currency.type.length == 3


def test_all_timestamp_columns_are_timezone_aware() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name.endswith("_at"):
                assert column.type.timezone is True, f"{table.name}.{column.name}"


def test_recommendation_and_audit_models_reject_updates() -> None:
    recommendation = models.RecommendationModel(
        id=uuid4(),
        user_id=uuid4(),
        analysis_id=uuid4(),
        version=1,
        recommended_action=models.RecommendationAction.KEEP,
        confidence=Decimal("0.8000"),
        rationale="Evidence supports keeping the subscription.",
        uncertainty_json={},
        monthly_savings_amount=Decimal("0"),
        annual_savings_amount=Decimal("0"),
        currency="NGN",
        prompt_version="1",
        schema_version="1",
        created_at=datetime.now(UTC),
    )
    audit_event = models.AuditEventModel(
        id=uuid4(),
        user_id=uuid4(),
        event_type="recommendation.created",
        actor_type="user",
        actor_id=uuid4(),
        resource_type="recommendation",
        resource_id=recommendation.id,
        payload_json={},
        occurred_at=datetime.now(UTC),
    )

    for record in (recommendation, audit_event):
        with pytest.raises(ValueError, match="immutable"):
            models.prevent_immutable_update(object(), object(), record)


def test_immutable_repositories_expose_no_update_or_delete_method() -> None:
    for repository in (RecommendationRepository, AuditEventRepository):
        assert not hasattr(repository, "update")
        assert not hasattr(repository, "delete")


def test_constraints_and_indexes_have_stable_names() -> None:
    for table in Base.metadata.tables.values():
        assert all(constraint.name for constraint in table.constraints)
        assert all(index.name for index in table.indexes)
