
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("move_plant_data")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import TimelineEvent, StopQueue
    from apps.plant_worker.rollup_agent import compute_daily_rollup # functionality might be embedded in worker loop, check imports
except ImportError as e:
    # If explicit import fails, we rely on DB update and letting the worker pick it up
    pass

def move_plant_to_today():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_date = now.date()
        
        # 1. Update TimelineEvents (The source for rollups)
        # Find the 6 Motor Overheat events from Jan 9 (or older)
        events = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc < today_date,
                TimelineEvent.payload_json.contains({"reason": "Motor Overheat"}) # dialect specific, simple string search easier or iterate
            )
        ).scalars().all()
        
        # Filter in python if dialect issue
        target_events = [e for e in events if "Motor Overheat" in str(e.payload_json)]
        
        log.info(f"Found {len(target_events)} old Motor Overheat events in Plant.")
        
        for e in target_events:
            e.occurred_at_utc = now
            # Also update duration if 0 (belt and suspenders)
            p = dict(e.payload_json)
            if p.get("duration_seconds", 0) < 60:
                p["duration_seconds"] = 900
            e.payload_json = p

        # 2. Update StopQueue (for consistency, though rollup might use Timeline)
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
        log.info(f"Moved {len(target_events)} events and {len(stops)} stop records to {now}.")

    finally:
        db.close()

if __name__ == "__main__":
    move_plant_to_today()
