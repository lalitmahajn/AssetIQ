
import sys
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("move_debug")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent
except ImportError as e:
    pass

def debug_and_move():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_date = now.date()
        
        # Fetch ALL stops older than today
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc < today_date
            )
        ).scalars().all()
        
        log.info(f"Found {len(events)} candidate STOP events older than {today_date}")
        
        moved_count = 0
        for e in events:
            p = e.payload_json or {}
            # Normalize to string dump for loose matching
            p_str = json.dumps(p).lower()
            
            # log the first few for inspection
            if moved_count < 3:
                log.info(f"Inspecting Event {e.id}: {p_str}")

            # LOOSE MATCHING: "motor" or "overheat"
            if "motor" in p_str or "overheat" in p_str:
                e.occurred_at_utc = now
                # Fix duration
                if p.get("duration_seconds", 0) < 60:
                    p["duration_seconds"] = 900
                    e.payload_json = p
                moved_count += 1
        
        if moved_count > 0:
            db.commit()
            log.info(f"Moved {moved_count} events to {now}")
        else:
            log.warning("No events matched 'motor' or 'overheat' filter!")

    finally:
        db.close()

if __name__ == "__main__":
    debug_and_move()
