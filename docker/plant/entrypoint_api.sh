#!/usr/bin/env sh
set -eu

: "${PLANT_DB_URL:?PLANT_DB_URL required}"
: "${JWT_SECRET:?JWT_SECRET required}"
: "${SYNC_HMAC_SECRET:?SYNC_HMAC_SECRET required}"
: "${STATION_SECRET_ENC_KEY:?STATION_SECRET_ENC_KEY required}"

python -m alembic upgrade head
exec uvicorn apps.plant_backend.plant_backend.main:app --host 0.0.0.0 --port 8000
