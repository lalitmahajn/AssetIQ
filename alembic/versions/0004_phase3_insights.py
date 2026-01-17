"""Phase-3 Intelligence: daily insights table

Revision ID: 0004_phase3_insights
Revises: 0003_hq_phase2
Create Date: 2026-01-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_phase3_insights"
down_revision = "0003_hq_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_insight_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("day_utc", sa.String(length=10), nullable=False, index=True),
        sa.Column("site_code", sa.String(length=16), nullable=True, index=True),
        sa.Column("insight_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="LOW"),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "day_utc", "site_code", "insight_type", "title", name="uq_insight_day_site_type_title"
        ),
    )


def downgrade() -> None:
    op.drop_table("hq_insight_daily")
