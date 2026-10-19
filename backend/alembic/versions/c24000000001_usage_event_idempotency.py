"""Add idempotency keys to usage events.

Revision ID: c24000000001
Revises: b12000000001
"""

import sqlalchemy as sa

from alembic import op

revision = "c24000000001"
down_revision = "b12000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usage_events",
        sa.Column(
            "idempotency_key",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_usage_events_user_id_source_idempotency_key",
        "usage_events",
        ["user_id", "source", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_usage_events_user_id_source_idempotency_key",
        "usage_events",
        type_="unique",
    )

    op.drop_column("usage_events", "idempotency_key")
