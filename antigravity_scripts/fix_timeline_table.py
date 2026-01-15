import os
from sqlalchemy import create_engine, text

db_url = os.environ.get("PLANT_DB_URL")
if not db_url:
    print("PLANT_DB_URL not set!")
    exit(1)

engine = create_engine(db_url)
conn = engine.connect()

print("Checking timeline tables...")

# Check for plural (correct) and singular (incorrect)
check_plural = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'timeline_events')")
check_singular = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'timeline_event')")

exists_plural = conn.execute(check_plural).scalar()
exists_singular = conn.execute(check_singular).scalar()

print(f"timeline_events exists: {exists_plural}")
print(f"timeline_event exists: {exists_singular}")

if exists_plural:
    print("Correct table 'timeline_events' already exists. Nothing to do.")
elif exists_singular:
    print("Found incorrect table 'timeline_event'. Renaming to 'timeline_events'...")
    try:
        conn.execute(text("ALTER TABLE timeline_event RENAME TO timeline_events"))
        conn.commit()
        print("Success: Renamed timeline_event -> timeline_events")
    except Exception as e:
        print(f"Error renaming: {e}")
else:
    print("Neither table exists. Creating 'timeline_events'...")
    create_sql = """
    CREATE TABLE IF NOT EXISTS timeline_events (
        id VARCHAR(50) PRIMARY KEY,
        site_code VARCHAR(50),
        asset_id VARCHAR(100),
        event_type VARCHAR(100),
        payload_json JSONB,
        occurred_at_utc TIMESTAMP WITHOUT TIME ZONE,
        correlation_id VARCHAR(100),
        created_at_utc TIMESTAMP WITHOUT TIME ZONE
    );
    """
    try:
        conn.execute(text(create_sql))
        conn.commit()
        print("Success: Created timeline_events")
    except Exception as e:
        print(f"Error creating: {e}")

conn.close()
