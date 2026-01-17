"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-08

"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("pin_hash", sa.String(length=128), nullable=False),
        sa.Column("roles", sa.String(length=256), nullable=False),
    )

    op.create_table(
        "stop_queue",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "is_open", sa.Boolean(), nullable=False, server_default=sa.text("true"), index=True
        ),
        sa.Column("opened_at_utc", sa.DateTime(), nullable=False),
        sa.Column("closed_at_utc", sa.DateTime(), nullable=True),
        sa.Column("resolution_text", sa.Text(), nullable=True),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="OPEN", index=True
        ),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("assigned_to_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("sla_due_at_utc", sa.DateTime(), nullable=True),
        sa.Column("close_note", sa.Text(), nullable=True),
    )

    op.create_table(
        "event_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("sent_at_utc", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "email_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("to_email", sa.String(length=256), nullable=False, index=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="PENDING", index=True
        ),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("sent_at_utc", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "ingest_dedup",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_id", "event_id", name="uq_source_event"),
    )

    op.create_table(
        "applied_correlation",
        sa.Column("correlation_id", sa.String(length=128), primary_key=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "dead_letter",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("payload_json", sa.String(), nullable=False),
        sa.Column("error", sa.String(length=300), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "rollup_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("day_utc", sa.String(length=16), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("stops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tickets_open", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faults", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("site_code", "day_utc", "asset_id", name="uq_rollup"),
    )


def downgrade() -> None:
    op.drop_table("rollup_daily")
    op.drop_table("dead_letter")
    op.drop_table("applied_correlation")
    op.drop_table("ingest_dedup")
    op.drop_table("email_queue")
    op.drop_table("event_outbox")
    op.drop_table("tickets")
    op.drop_table("stop_queue")
    op.drop_table("users")
