
import sys
import logging
from datetime import datetime
from apps.hq_backend.intelligence import recompute_and_store_daily_insights
from common_core.logging_setup import configure_logging

configure_logging(component="force_intelligence")
log = logging.getLogger("force_intelligence")

# We want to force calculation for TODAY (since we simulated data for today)
today_iso = datetime.utcnow().date().isoformat()

print(f"Force recomputing insights for day: {today_iso} ...")

try:
    count = recompute_and_store_daily_insights(today_iso, window_days=14)
    print(f"Success! Generated {count} insight(s).")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
