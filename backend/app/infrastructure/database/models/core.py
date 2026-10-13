from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.subscriptions.entities import SubscriptionStatus as SubscriptionStatus
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecommendationAction(enum.StrEnum):
    KEEP = "keep"
    DOWNGRADE = "downgrade"
    CANCEL = "cancel"
    REVIEW = "review"


class DecisionType(enum.StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"
    DEFER = "defer"


class SavingsKind(enum.StrEnum):
    ESTIMATED = "estimated"
    VERIFIED = "verified"


def enum_type(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class UserOwnedMixin:
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )


class ImmutableRecord:
    """Marker for records that normal persistence code must never update."""


class ProviderModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "providers"

    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)


class ConsentModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "consents"

    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderConnectionModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "provider_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider_id", "external_reference"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PlanModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        UniqueConstraint("provider_id", "external_reference"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(30), nullable=False)


class SubscriptionModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "subscriptions"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_connections.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_type(SubscriptionStatus, "subscription_status"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    renewal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SubscriptionAlternativeModel(Base):
    __tablename__ = "subscription_alternatives"
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class TransactionModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        UniqueConstraint("user_id", "source", "external_reference"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(255))


class UsageEventModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "usage_events"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    is_unknown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PromptVersionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AnalysisModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "analyses"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[WorkStatus] = mapped_column(
        enum_type(WorkStatus, "analysis_status"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationModel(UUIDPrimaryKeyMixin, UserOwnedMixin, ImmutableRecord, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("monthly_savings_amount >= 0", name="monthly_savings_non_negative"),
        CheckConstraint("annual_savings_amount >= 0", name="annual_savings_non_negative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        UniqueConstraint("analysis_id", "version"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_action: Mapped[RecommendationAction] = mapped_column(
        enum_type(RecommendationAction, "recommendation_action"), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    monthly_savings_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    annual_savings_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecommendationEvidenceModel(UUIDPrimaryKeyMixin, UserOwnedMixin, ImmutableRecord, Base):
    __tablename__ = "recommendation_evidence"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_table: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column()
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecommendationDecisionModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "recommendation_decisions"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recommendation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[DecisionType] = mapped_column(
        enum_type(DecisionType, "decision_type"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    correction_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    defer_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "actions"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)

    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation_decisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[WorkStatus] = mapped_column(
        enum_type(WorkStatus, "action_status"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class SavingsRecordModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "savings_records"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
    )

    action_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("actions.id", ondelete="SET NULL"), index=True
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kind: Mapped[SavingsKind] = mapped_column(
        enum_type(SavingsKind, "savings_kind"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period: Mapped[str] = mapped_column(String(30), nullable=False)
    calculation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ConversationModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "conversations"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )


class MessageModel(UUIDPrimaryKeyMixin, TimestampMixin, UserOwnedMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class EvaluationRunModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[WorkStatus] = mapped_column(
        enum_type(WorkStatus, "evaluation_status"), nullable=False
    )
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class EvaluationResultModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (UniqueConstraint("evaluation_run_id", "case_id"),)

    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(String(150), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AuditEventModel(UUIDPrimaryKeyMixin, ImmutableRecord, Base):
    __tablename__ = "audit_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column()
    correlation_id: Mapped[str | None] = mapped_column(String(100), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_subscriptions_user_id_status", SubscriptionModel.user_id, SubscriptionModel.status)
Index("ix_analyses_user_id_status", AnalysisModel.user_id, AnalysisModel.status)
Index("ix_actions_user_id_status", ActionModel.user_id, ActionModel.status)


def prevent_immutable_update(_mapper: object, _connection: object, target: object) -> None:
    raise ValueError(f"{type(target).__name__} records are immutable")


for immutable_model in (RecommendationModel, RecommendationEvidenceModel, AuditEventModel):
    event.listen(immutable_model, "before_update", prevent_immutable_update)
