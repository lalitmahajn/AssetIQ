---
trigger: always_on
---

When modifying SQLAlchemy models (models.py files):
- Always create a corresponding Alembic migration using MIGRATION_TARGET=plant or MIGRATION_TARGET=hq
- Review auto-generated migrations and remove any DROP statements for tables belonging to the wrong database
- Test on fresh database: docker-compose down -v, then up -d --build

Plant-only tables: users, stop_queue, plc_config, plc_tags, tickets, ticket_activities, event_outbox, email_queue, whatsapp_queue, ingest_dedup, timeline_events, audit_log, dead_letter, assets, master_types, master_items, reason_suggestions, report_requests, stations, system_config

HQ-only tables: hq_plants, applied_correlation, dead_letter, rollup_daily, ticket_snapshot, hq_timeline_event, stop_reason_daily, email_queue, report_job, hq_insight_daily, hq_users

Docker entrypoints must: be in /usr/local/bin (not /app), run init_db.py before alembic, use ENTRYPOINT directive.