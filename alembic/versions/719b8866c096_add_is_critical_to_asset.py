"""Add is_critical to Asset

Revision ID: 719b8866c096
Revises: 30074ed22c57
Create Date: 2026-01-19 09:55:22.227033

"""

import sqlalchemy as sa

from alembic import op

revision = "719b8866c096"
down_revision = "30074ed22c57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets", sa.Column("is_critical", sa.Boolean(), nullable=False, server_default="false")
    )


def downgrade() -> None:
    op.drop_column("assets", "is_critical")
