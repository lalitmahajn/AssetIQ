
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("move_plant_simple")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent, StopQueue
except ImportError as e:
    pass

def move_plant_simple():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_date = now.date()
        
        # Fetch ALL stops older than today (safer query)
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc < today_date
            )
        ).scalars().all()
        
        moved_count = 0
        for e in events:
            # Filter in Python
            p = e.payload_json or {}
            reason = p.get("reason_code") or p.get("reason", "")
            
            if "Motor Overheat" in reason:
                e.occurred_at_utc = now
                if p.get("duration_seconds", 0) < 60:
                    p["duration_seconds"] = 900
                    e.payload_json = p
                moved_count += 1
        
        # Update StopQueue
        stops = db.execute(
            select(StopQueue).where(
                StopQueue.reason == "Motor Overheat",
                StopQueue.opened_at_utc < today_date
            )
        ).scalars().all()
        
        for s in stops:
            s.opened_at_utc = now
            s.closed_at_utc = now + timedelta(minutes=15)
            
        db.commit()
        log.info(f"Successfully moved {moved_count} TimelineEvents and {len(stops)} StopQueue records to {now}.")
        
    except Exception as e:
        log.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    move_plant_simple()
