from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text

from common_core.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)
    full_name = Column(String(128), nullable=True)
    pin_hash = Column(String(128), nullable=False)
    roles = Column(String(256), nullable=False)


class StopQueue(Base):
    __tablename__ = "stop_queue"
    id = Column(String(64), primary_key=True)
    site_code = Column(String(16), nullable=False, index=True)
    asset_id = Column(String(128), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    is_open = Column(Boolean, nullable=False, index=True, default=True)
    opened_at_utc = Column(DateTime, nullable=False)
    closed_at_utc = Column(DateTime, nullable=True)
    resolution_text = Column(Text, nullable=True)
    live_context_json = Column(JSON, nullable=True)


class PLCConfig(Base):
    __tablename__ = "plc_config"
    id = Column(String(64), primary_key=True)
    site_code = Column(String(16), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    protocol = Column(String(32), nullable=False)  # MODBUS_TCP, MODBUS_RTU
    ip_address = Column(String(128), nullable=True)
    port = Column(Integer, nullable=True)
    serial_port = Column(String(128), nullable=True)  # COM1, /dev/ttyUSB0
    baud_rate = Column(Integer, nullable=True, default=9600)
    slave_id = Column(Integer, nullable=False, default=1)
    scan_interval_sec = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at_utc = Column(DateTime, nullable=False)


class PLCTag(Base):
    __tablename__ = "plc_tags"
    id = Column(String(64), primary_key=True)
    plc_id = Column(String(64), nullable=False, index=True)
    tag_name = Column(String(128), nullable=False, index=True)
    address = Column(Integer, nullable=False)
    data_type = Column(String(32), nullable=False, default="BOOL")  # BOOL, INT16, FLOAT32
    multiplier = Column(Float, nullable=True, default=1.0)  # Scaling factor
    is_stop_trigger = Column(Boolean, nullable=False, default=False)
    trigger_value = Column(
        Float, nullable=True
    )  # If match this value, trigger stop (usually 1 for BOOL)
    stop_reason_template = Column(
        String(256), nullable=True
    )  # e.g. "Low Pressure: $pressure_tag psi"
    asset_id = Column(String(128), nullable=True)  # Asset to associate stop with


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String(64), primary_key=True)
    site_code = Column(String(16), nullable=False, index=True)
    asset_id = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False, index=True, default="OPEN")
    priority = Column(String(32), nullable=False, default="MEDIUM")
    assigned_to_user_id = Column(String(64), nullable=True)
    assigned_dept = Column(String(64), nullable=True)
    source = Column(String(32), nullable=False, default="MANUAL")  # MANUAL, AUTO
    stop_id = Column(String(64), nullable=True, index=True)  # Link to StopQueue/Timeline
    created_at_utc = Column(DateTime, nullable=False, index=True)
    sla_due_at_utc = Column(DateTime, nullable=True, index=True)
    acknowledged_at_utc = Column(DateTime, nullable=True)
    resolved_at_utc = Column(DateTime, nullable=True)
    resolution_reason = Column(String(64), nullable=True)  # Root cause code
    close_note = Column(Text, nullable=True)
    sla_warning_sent = Column(Boolean, nullable=False, default=False)  # Track if warning alert sent


class TicketActivity(Base):
    __tablename__ = "ticket_activities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=True)  # User ID or "SYSTEM"
    activity_type = Column(String(32), nullable=False)  # CREATED, ACK, NOTE, STATUS_CHANGE, CLOSED
    details = Column(String(512), nullable=True)
    created_at_utc = Column(DateTime, nullable=False)


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    payload_json = Column(JSON, nullable=False)
    correlation_id = Column(String(128), nullable=False, unique=True)
    created_at_utc = Column(DateTime, nullable=False)
    sent_at_utc = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_attempt_at_utc = Column(DateTime, nullable=True)
    last_error = Column(String(300), nullable=True)


class EmailQueue(Base):
    __tablename__ = "email_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    to_email = Column(String(256), nullable=False, index=True)
    subject = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True, default="PENDING")
    created_at_utc = Column(DateTime, nullable=False)
    sent_at_utc = Column(DateTime, nullable=True)


class WhatsAppQueue(Base):
    __tablename__ = "whatsapp_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(64), nullable=False, index=True)
    phone_number = Column(String(512), nullable=False)  # Increased for multiple targets
    message = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True, default="PENDING")
    sla_state = Column(String(16), nullable=True)  # OK, WARNING, BREACHED
    created_at_utc = Column(DateTime, nullable=False)
    sent_at_utc = Column(DateTime, nullable=True)


class IngestDedup(Base):
    __tablename__ = "ingest_dedup"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(64), nullable=False)
    event_id = Column(String(128), nullable=False)
    created_at_utc = Column(DateTime, nullable=False)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id = Column(String(64), primary_key=True)
    site_code = Column(String(16), nullable=False, index=True)
    asset_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload_json = Column(JSON, nullable=False)
    occurred_at_utc = Column(DateTime, nullable=False, index=True)
    correlation_id = Column(String(128), nullable=False, unique=True)
    created_at_utc = Column(DateTime, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    actor_station_code = Column(String(64), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    request_id = Column(String(64), nullable=True, index=True)
    details_json = Column(JSON, nullable=False)
    created_at_utc = Column(DateTime, nullable=False, index=True)


class DeadLetter(Base):
    __tablename__ = "dead_letter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=False, index=True)
    payload_json = Column(String(), nullable=False)
    error = Column(String(300), nullable=False)
    created_at_utc = Column(DateTime, nullable=False)


class Asset(Base):
    __tablename__ = "assets"
    id = Column(String(64), primary_key=True)
    site_code = Column(String(16), nullable=False, index=True)
    asset_code = Column(String(64), nullable=False, index=True)  # human readable unique code
    name = Column(String(256), nullable=False, index=True)
    description = Column(Text, nullable=True)  # Added for UI compatibility
    category = Column(String(128), nullable=False)
    parent_id = Column(String(64), nullable=True, index=True)
    criticality = Column(String(32), nullable=False, default="medium")
    tags = Column(JSON, nullable=False, default=list)
    location_area = Column(String(128), nullable=True)
    location_line = Column(String(128), nullable=True)
    status = Column(String(16), nullable=False, default="active")
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=True)
    created_by_user_id = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_critical = Column(Boolean, default=False, nullable=False)


class MasterType(Base):
    __tablename__ = "master_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    type_code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=True)

    from sqlalchemy import Index, UniqueConstraint

    __table_args__ = (
        UniqueConstraint("site_code", "type_code", name="uq_master_types_site_type"),
        Index("ix_master_types_site_active", "site_code", "is_active"),
    )


class MasterItem(Base):
    __tablename__ = "master_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    master_type_code = Column(String(64), nullable=False, index=True)
    item_code = Column(String(64), nullable=False)
    item_name = Column(String(160), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    meta_json = Column(JSON, nullable=False, default=dict)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=True)

    from sqlalchemy import Index, UniqueConstraint

    __table_args__ = (
        UniqueConstraint(
            "site_code", "master_type_code", "item_code", name="uq_master_items_site_type_code"
        ),
        Index("ix_master_items_site_type_active", "site_code", "master_type_code", "is_active"),
    )


class ReasonSuggestion(Base):
    __tablename__ = "reason_suggestions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    master_type_code = Column(String(64), nullable=False, index=True, default="STOP_REASON")
    suggested_name = Column(String(256), nullable=False)
    normalized_key = Column(String(256), nullable=False, index=True)
    count = Column(Integer, nullable=False, default=1)
    status = Column(
        String(24), nullable=False, default="pending"
    )  # pending|auto_promoted|approved|rejected|merged
    threshold = Column(Integer, nullable=False, default=5)
    last_examples_json = Column(JSON, nullable=False, default=list)
    approved_master_item_id = Column(Integer, nullable=True)
    merged_into_master_item_id = Column(Integer, nullable=True)
    created_by_user_id = Column(String(64), nullable=True)
    reviewed_by_user_id = Column(String(64), nullable=True)
    reviewed_at_utc = Column(DateTime, nullable=True)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class ReportRequest(Base):
    __tablename__ = "report_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_code = Column(String(16), nullable=False, index=True)
    report_type = Column(String(64), nullable=False, index=True)
    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)
    filters_json = Column(Text, nullable=False, default="{}")
    requested_by_user_id = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False, index=True)  # requested|generated|failed
    generated_file_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at_utc = Column(DateTime, nullable=False)
    updated_at_utc = Column(DateTime, nullable=True)


class Station(Base):
    __tablename__ = "stations"
    station_code = Column(String(32), primary_key=True)
    description = Column(String(128), nullable=True)
    secret_hash = Column(String(128), nullable=False)
    token_salt = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at_utc = Column(DateTime, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_config"
    config_key = Column(String(64), primary_key=True)
    config_value = Column(JSON, nullable=False)
    updated_at_utc = Column(DateTime, nullable=False)
