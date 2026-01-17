"""timeline + audit + outbox retry metadata

Revision ID: 0002_timeline_audit_retry
Revises: 0001_initial
Create Date: 2026-01-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_timeline_audit_retry"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("actor_station_code", sa.String(length=64), nullable=True, index=True),
        sa.Column("action", sa.String(length=64), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("request_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    )

    op.add_column(
        "event_outbox", sa.Column("next_attempt_at_utc", sa.DateTime(), nullable=True, index=True)
    )
    op.add_column("event_outbox", sa.Column("last_error", sa.String(length=300), nullable=True))

    op.add_column("tickets", sa.Column("acknowledged_at_utc", sa.DateTime(), nullable=True))
    op.add_column("tickets", sa.Column("resolved_at_utc", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "resolved_at_utc")
    op.drop_column("tickets", "acknowledged_at_utc")
    op.drop_column("event_outbox", "last_error")
    op.drop_column("event_outbox", "next_attempt_at_utc")
    op.drop_table("audit_log")
    op.drop_table("timeline_events")
