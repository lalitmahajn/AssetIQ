"""HQ Phase-2 tables (multi-plant visibility)

Revision ID: 0003_hq_phase2
Revises: 0002_timeline_audit_retry
Create Date: 2026-01-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_hq_phase2"
down_revision = "0002_timeline_audit_retry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_plants",
        sa.Column("site_code", sa.String(length=16), primary_key=True),
        sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at_utc", sa.DateTime(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=False),
    )

    # op.create_table(
    #     "applied_correlation",
    #     sa.Column("correlation_id", sa.String(length=128), primary_key=True),
    #     sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    # )

    # op.create_table(
    #     "dead_letter",
    #     sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    #     sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
    #     sa.Column("entity_type", sa.String(length=32), nullable=False),
    #     sa.Column("entity_id", sa.String(length=64), nullable=False),
    #     sa.Column("correlation_id", sa.String(length=128), nullable=False),
    #     sa.Column("payload_json", sa.Text(), nullable=False),
    #     sa.Column("error", sa.String(length=300), nullable=False),
    #     sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    # )

    op.drop_table("rollup_daily")  # Re-creating with new schema per 0003
    op.create_table(
        "rollup_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("day_utc", sa.String(length=10), nullable=False, index=True),
        sa.Column("stops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faults", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tickets_open", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sla_breaches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("site_code", "day_utc", name="uq_rollup_site_day"),
    )

    op.create_table(
        "ticket_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("ticket_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("title", sa.String(length=256), nullable=False, server_default=""),
        sa.Column(
            "status", sa.String(length=32), nullable=False, index=True, server_default="OPEN"
        ),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("sla_due_at_utc", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at_utc", sa.DateTime(), nullable=True),
        sa.Column("resolved_at_utc", sa.DateTime(), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("site_code", "ticket_id", name="uq_ticket_site_ticket"),
    )

    op.create_table(
        "hq_timeline_event",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("event_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("occurred_at_utc", sa.DateTime(), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=128), nullable=True, index=True),
        sa.Column("reason_code", sa.String(length=64), nullable=True, index=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("site_code", "event_id", name="uq_hq_event_site_event"),
    )

    op.create_table(
        "stop_reason_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_code", sa.String(length=16), nullable=False, index=True),
        sa.Column("day_utc", sa.String(length=10), nullable=False, index=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("stops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "site_code", "day_utc", "reason_code", name="uq_reason_site_day_reason"
        ),
    )

    # op.create_table(
    #     "email_queue",
    #     sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    #     sa.Column("to_email", sa.String(length=256), nullable=False, index=True),
    #     sa.Column("subject", sa.String(length=256), nullable=False),
    #     sa.Column("body", sa.Text(), nullable=False),
    #     sa.Column("status", sa.String(length=32), nullable=False, index=True, server_default="PENDING"),
    #     sa.Column("created_at_utc", sa.DateTime(), nullable=False),
    #     sa.Column("sent_at_utc", sa.DateTime(), nullable=True),
    # )

    op.create_table(
        "report_job",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("period_start_utc", sa.String(length=10), nullable=False),
        sa.Column("period_end_utc", sa.String(length=10), nullable=False),
        sa.Column("file_pdf", sa.String(length=512), nullable=True),
        sa.Column("file_xlsx", sa.String(length=512), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "report_type", "period_start_utc", "period_end_utc", name="uq_report_period"
        ),
    )


def downgrade() -> None:
    op.drop_table("report_job")
    op.drop_table("email_queue")
    op.drop_table("stop_reason_daily")
    op.drop_table("hq_timeline_event")
    op.drop_table("ticket_snapshot")
    op.drop_table("rollup_daily")
    op.drop_table("dead_letter")
    op.drop_table("applied_correlation")
    op.drop_table("hq_plants")
