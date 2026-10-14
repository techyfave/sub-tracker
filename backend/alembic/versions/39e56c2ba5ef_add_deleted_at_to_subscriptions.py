"""add deleted_at to subscriptions

Revision ID: 39e56c2ba5ef
Revises: d080cbbc9e77
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "39e56c2ba5ef"
down_revision: str | None = "d080cbbc9e77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "deleted_at")
