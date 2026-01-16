"""Add hq_users table

Revision ID: 0007_add_hq_users
Revises: 6d85ac6521e8
Create Date: 2026-01-15 15:05:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_hq_users"
down_revision = "6d85ac6521e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_users",
        sa.Column("username", sa.String(length=64), primary_key=True),
        sa.Column("pin_hash", sa.String(length=128), nullable=False),
        sa.Column("roles", sa.String(length=256), nullable=False, server_default="admin"),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("hq_users")
