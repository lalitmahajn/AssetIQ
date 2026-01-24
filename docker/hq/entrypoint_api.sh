#!/usr/bin/env sh
set -eu

: "${HQ_DB_URL:?HQ_DB_URL required}"
: "${JWT_SECRET:?JWT_SECRET required}"
: "${SYNC_HMAC_SECRET:?SYNC_HMAC_SECRET required}"
: "${STATION_SECRET_ENC_KEY:?STATION_SECRET_ENC_KEY required}"

echo "=== HQ Backend Startup ==="

# Step 0: Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until python -c "
import sys
from sqlalchemy import create_engine, text
import os
try:
    engine = create_engine(os.environ['HQ_DB_URL'])
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('PostgreSQL is ready!')
    sys.exit(0)
except Exception as e:
    print(f'Waiting... {e}')
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done

# Step 1: Create tables from SQLAlchemy models (safe, idempotent)
echo "Initializing database tables from models..."
python -m apps.hq_backend.init_db

# Step 2: Run Alembic migrations for any incremental changes
echo "Running Alembic migrations..."
MIGRATION_TARGET=hq python -m alembic upgrade head || echo "Alembic migrations skipped or failed (tables may already exist)"

# Step 3: Start the application
echo "Starting HQ Backend..."
exec uvicorn apps.hq_backend.main:app --host 0.0.0.0 --port 8100
