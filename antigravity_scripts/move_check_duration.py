
import sys
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("check_duration")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent
except ImportError as e:
    pass

def check_and_fix():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_date = now.date()
        
        # Fetch ALL stops TODAY
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc >= today_date
            )
        ).scalars().all()
        
        log.info(f"Found {len(events)} STOP events TODAY ({today_date})")
        
        fixed_count = 0
        total_duration = 0
        for e in events:
            p = dict(e.payload_json or {})
            d = p.get("duration_seconds", 0)
            total_duration += d
            
            # log occasional
            if fixed_count < 3 and d == 0:
                log.info(f"Event {e.id} has 0 duration! Payload: {p}")

            if d < 60:
                p["duration_seconds"] = 900
                e.payload_json = p
                fixed_count += 1
        
        log.info(f"Total Duration before fix: {total_duration}")
        
        if fixed_count > 0:
            db.commit()
            log.info(f"Fixed duration for {fixed_count} events.")
        else:
            log.info("No events needed duration fix.")

    finally:
        db.close()

if __name__ == "__main__":
    check_and_fix()
