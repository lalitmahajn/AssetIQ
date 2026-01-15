import os
from sqlalchemy import create_engine, text

db_url = os.environ.get("PLANT_DB_URL")
if not db_url:
    print("PLANT_DB_URL not set!")
    exit(1)

engine = create_engine(db_url)
conn = engine.connect()

statements = [
    # Add missing columns to tickets ( idempotency guaranteed by IF NOT EXISTS)
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_due_at_utc TIMESTAMP WITHOUT TIME ZONE;",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR(50);",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_to_user_id VARCHAR(50);",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS acknowledged_at_utc TIMESTAMP WITHOUT TIME ZONE;",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolved_at_utc TIMESTAMP WITHOUT TIME ZONE;",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS close_note TEXT;",

    # Add missing columns to event_outbox (New retry logic)
    "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;",
    "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS next_attempt_at_utc TIMESTAMP WITHOUT TIME ZONE;",
    "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS last_error VARCHAR(300);",

    # Create missing tables
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        site_code VARCHAR(50),
        actor_user_id VARCHAR(50),
        actor_station_code VARCHAR(50),
        action VARCHAR(100),
        entity_type VARCHAR(50),
        entity_id VARCHAR(100),
        request_id VARCHAR(100),
        details_json JSONB,
        created_at_utc TIMESTAMP WITHOUT TIME ZONE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS timeline_event (
        id VARCHAR(50) PRIMARY KEY,
        site_code VARCHAR(50),
        asset_id VARCHAR(100),
        event_type VARCHAR(100),
        payload_json JSONB,
        occurred_at_utc TIMESTAMP WITHOUT TIME ZONE,
        correlation_id VARCHAR(100),
        created_at_utc TIMESTAMP WITHOUT TIME ZONE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id SERIAL PRIMARY KEY,
        site_code VARCHAR(50),
        entity_type VARCHAR(50),
        entity_id VARCHAR(100),
        payload_json JSONB,
        correlation_id VARCHAR(100),
        created_at_utc TIMESTAMP WITHOUT TIME ZONE,
        sent_at_utc TIMESTAMP WITHOUT TIME ZONE,
        retry_count INTEGER,
        next_attempt_at_utc TIMESTAMP WITHOUT TIME ZONE,
        last_error TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS email_queue (
        id SERIAL PRIMARY KEY,
        to_email VARCHAR(255),
        subject VARCHAR(255),
        body TEXT,
        status VARCHAR(50),
        created_at_utc TIMESTAMP WITHOUT TIME ZONE,
        sent_at_utc TIMESTAMP WITHOUT TIME ZONE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS stop_queue (
        id VARCHAR(50) PRIMARY KEY,
        site_code VARCHAR(50),
        asset_id VARCHAR(100),
        reason TEXT,
        is_open BOOLEAN,
        opened_at_utc TIMESTAMP WITHOUT TIME ZONE,
        closed_at_utc TIMESTAMP WITHOUT TIME ZONE,
        resolution_text TEXT
    );
    """
]

print("Starting schema repair...")
try:
    for s in statements:
        print(f"Executing statement...")
        conn.execute(text(s))
    conn.commit()
    print("Schema repair complete.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
