import os
import sqlalchemy
from sqlalchemy import create_engine, text

db_url = os.environ.get("PLANT_DB_URL")
if not db_url:
    print("PLANT_DB_URL not set!")
    exit(1)

engine = create_engine(db_url)
conn = engine.connect()

print("Checking event_outbox columns...")

# Check text
check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='event_outbox'")
result = conn.execute(check_sql)
columns = [row[0] for row in result.fetchall()]
print(f"Current columns: {columns}")

statements = [
    ("retry_count", "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;"),
    ("next_attempt_at_utc", "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS next_attempt_at_utc TIMESTAMP WITHOUT TIME ZONE;"),
    ("last_error", "ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS last_error VARCHAR(300);")
]

try:
    for col, sql in statements:
        if col in columns:
            print(f"Column {col} already exists.")
        else:
            print(f"Adding column {col}...")
            conn.execute(text(sql))
            conn.commit()
            print(f"Added {col}.")
    
    # Re-verify
    result = conn.execute(check_sql)
    new_columns = [row[0] for row in result.fetchall()]
    print(f"Final columns: {new_columns}")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
