
import sys
import logging
from datetime import datetime, timedelta
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, TimelineEvent
from apps.plant_backend.services import _new_id

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed_stops")

def seed():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_date = now.date()
        
        # Insert 6 stops
        for i in range(6):
            stop_id = _new_id("STOP")
            asset = f"CONVEYOR-0{i%5 + 1}"
            reason = "Motor Overheat"
            
            # StopQueue
            sq = StopQueue(
                id=stop_id,
                site_code="P01",
                asset_id=asset,
                reason=reason,
                is_open=False, # Closed
                opened_at_utc=now,
                closed_at_utc=now + timedelta(minutes=15),
                resolution_text="Auto Resolved by Seed"
            )
            db.add(sq)
            
            # TimelineEvent
            te_id = _new_id("EVT")
            te = TimelineEvent(
                id=te_id,
                site_code="P01",
                event_type="STOP",
                asset_id=asset,
                occurred_at_utc=now,
                created_at_utc=now,
                correlation_id=f"seed:{te_id}",
                payload_json={
                    "stop_id": stop_id,
                    "reason": reason,
                    "duration_seconds": 900 # 15 mins
                }
            )
            db.add(te)
            
        db.commit()
        log.info("Seeded 6 Motor Overheat stops (90 mins total) for today.")
        
    except Exception as e:
        log.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
