
import sys
import logging
from sqlalchemy import select, func
from typing import Any

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("audit_plant")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent
except ImportError as e:
    pass

def audit():
    db = PlantSessionLocal()
    try:
        # Count by date
        # Sqlite/Postgres truncate date logic differs, so we fetch all and agg in python to be safe
        events = db.execute(select(TimelineEvent.occurred_at_utc, TimelineEvent.event_type)).all()
        
        counts = {}
        for (ts, et) in events:
            d = ts.date().isoformat()
            k = f"{d} ({et})"
            counts[k] = counts.get(k, 0) + 1
            
        log.info("TimelineEvent Distribution:")
        for k, v in sorted(counts.items()):
            log.info(f"  {k}: {v}")
            
    finally:
        db.close()

if __name__ == "__main__":
    audit()
