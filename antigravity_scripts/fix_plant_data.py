
import sys
import logging
from sqlalchemy import select, update

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fix_plant")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fix_plant_events():
    db = PlantSessionLocal()
    try:
        # Find raw events with 0 duration for Motor Overheat (STOP events)
        # Note: In plant, payload_json stores the duration_seconds if the event was closed.
        
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc >= "2026-01-09", # Catch both days
            )
        ).scalars().all()
        
        updated = 0
        for e in events:
            p = e.payload_json or {}
            reason = p.get("reason_code") or p.get("reason")
            dur = p.get("duration_seconds", 0)
            
            if reason == "Motor Overheat" and (dur == 0 or dur is None):
                # Update payload
                new_payload = dict(p)
                new_payload["duration_seconds"] = 900
                e.payload_json = new_payload
                updated += 1
                
        db.commit()
        log.info(f"Successfully patched {updated} Plant TimelineEvent records to 900s duration.")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_plant_events()
