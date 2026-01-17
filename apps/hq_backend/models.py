from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from common_core.db import Base


class PlantRegistry(Base):
    __tablename__ = "hq_plants"
    site_code = Column(String(16), primary_key=True)
    display_name = Column(String(128), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen_at_utc = Column(DateTime, nullable=True)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=False)


class AppliedCorrelation(Base):
    __tablename__ = "applied_correlation"
    correlation_id = Column(String(128), primary_key=True)
    created_at_utc = Column(DateTime, nullable=False)


class DeadLetter(Base):
    __tablename__ = "dead_letter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(String(64), nullable=False)
    correlation_id = Column(String(128), nullable=False)
    payload_json = Column(Text, nullable=False)
    error = Column(String(300), nullable=False)
    created_at_utc = Column(DateTime, nullable=False)


class RollupDaily(Base):
    __tablename__ = "rollup_daily"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    day_utc = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    stops = Column(Integer, nullable=False, default=0)
    faults = Column(Integer, nullable=False, default=0)
    tickets_open = Column(Integer, nullable=False, default=0)
    sla_breaches = Column(Integer, nullable=False, default=0)
    downtime_minutes = Column(Integer, nullable=False, default=0)
    updated_at_utc = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("site_code", "day_utc", name="uq_rollup_site_day"),)


class TicketSnapshot(Base):
    __tablename__ = "ticket_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    ticket_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False, default="")
    status = Column(String(32), nullable=False, index=True, default="OPEN")
    priority = Column(String(32), nullable=False, default="MEDIUM")
    created_at_utc = Column(DateTime, nullable=False)
    sla_due_at_utc = Column(DateTime, nullable=True)
    acknowledged_at_utc = Column(DateTime, nullable=True)
    resolved_at_utc = Column(DateTime, nullable=True)
    updated_at_utc = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("site_code", "ticket_id", name="uq_ticket_site_ticket"),)


class TimelineEventHQ(Base):
    __tablename__ = "hq_timeline_event"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    occurred_at_utc = Column(DateTime, nullable=False, index=True)
    asset_id = Column(String(128), nullable=True, index=True)
    reason_code = Column(String(64), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=False, default=0)
    payload_json = Column(JSON, nullable=False, default={})

    __table_args__ = (UniqueConstraint("site_code", "event_id", name="uq_hq_event_site_event"),)


class StopReasonDaily(Base):
    __tablename__ = "stop_reason_daily"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    day_utc = Column(String(10), nullable=False, index=True)
    reason_code = Column(String(64), nullable=False, index=True)
    stops = Column(Integer, nullable=False, default=0)
    downtime_minutes = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("site_code", "day_utc", "reason_code", name="uq_reason_site_day_reason"),
    )


class EmailQueue(Base):
    __tablename__ = "email_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    to_email = Column(String(256), nullable=False, index=True)
    subject = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True, default="PENDING")
    created_at_utc = Column(DateTime, nullable=False)
    sent_at_utc = Column(DateTime, nullable=True)


class ReportJob(Base):
    __tablename__ = "report_job"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(32), nullable=False, index=True)  # DAILY/WEEKLY/MONTHLY
    period_start_utc = Column(String(10), nullable=False)  # YYYY-MM-DD
    period_end_utc = Column(String(10), nullable=False)  # YYYY-MM-DD inclusive
    file_pdf = Column(String(512), nullable=True)
    file_xlsx = Column(String(512), nullable=True)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "report_type", "period_start_utc", "period_end_utc", name="uq_report_period"
        ),
    )


class InsightDaily(Base):
    __tablename__ = "hq_insight_daily"
    id = Column(Integer, primary_key=True, autoincrement=True)
    day_utc = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    site_code = Column(String(16), nullable=True, index=True)  # null => global insight
    insight_type = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(16), nullable=False, default="LOW")  # LOW/MEDIUM/HIGH
    detail_json = Column(JSON, nullable=False, default=dict)
    created_at_utc = Column(DateTime, nullable=False)


class HQUser(Base):
    __tablename__ = "hq_users"
    username = Column(String(64), primary_key=True)
    pin_hash = Column(String(128), nullable=False)
    roles = Column(String(256), nullable=False, default="admin")
    created_at_utc = Column(DateTime, nullable=False)
