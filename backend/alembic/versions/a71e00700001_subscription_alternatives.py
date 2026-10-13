"""Persist alternative plans using the existing plan catalog.

Revision ID: a71e00700001
Revises: 39e56c2ba5ef
"""

import sqlalchemy as sa

from alembic import op

revision = "a71e00700001"
down_revision = "39e56c2ba5ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_alternatives",
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("subscription_id", "plan_id"),
    )


def downgrade() -> None:
    op.drop_table("subscription_alternatives")
