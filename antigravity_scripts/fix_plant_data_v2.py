
import sys
import logging
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fix_plant_v2")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fix_plant_events_force():
    db = PlantSessionLocal()
    try:
        # Select ALL stops from the last few days
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc >= "2026-01-01"
            )
        ).scalars().all()
        
        updated = 0
        for e in events:
            p = e.payload_json or {}
            dur = p.get("duration_seconds", 0)
            
            # If duration is effectively zero, FORCE fix it
            if dur < 60:
                new_payload = dict(p)
                new_payload["duration_seconds"] = 900
                e.payload_json = new_payload
                updated += 1
                
        db.commit()
        log.info(f"Force-patched {updated} Plant TimelineEvent records to 900s duration.")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_plant_events_force()
