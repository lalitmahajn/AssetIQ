
import sys
import logging
from datetime import datetime, timedelta
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, TimelineEvent
from apps.plant_backend.services import _new_id

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed_pattern")

def seed_jam():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        dates = [
            now,
            now - timedelta(days=1),
            now - timedelta(days=2)
        ]
        
        reason = "Jam at Sensor 7"
        
        count = 0
        for d in dates:
            # Insert 2 stops per day
            for i in range(2):
                stop_id = _new_id("STOP")
                asset = "CONVEYOR-02"
                
                # StopQueue
                sq = StopQueue(
                    id=stop_id,
                    site_code="P01",
                    asset_id=asset,
                    reason=reason,
                    is_open=False, 
                    opened_at_utc=d,
                    closed_at_utc=d + timedelta(minutes=10),
                    resolution_text="Auto Cleared"
                )
                db.add(sq)
                
                # Timeline
                te_id = _new_id("EVT")
                te = TimelineEvent(
                    id=te_id,
                    site_code="P01",
                    event_type="STOP",
                    asset_id=asset,
                    occurred_at_utc=d,
                    created_at_utc=d,
                    correlation_id=f"seed_pattern:{stop_id}",
                    payload_json={
                        "stop_id": stop_id,
                        "reason": reason,
                        "duration_seconds": 600
                    }
                )
                db.add(te)
                count += 1
                
        db.commit()
        log.info(f"Seeded {count} stops for '{reason}' across 3 days.")
        
    except Exception as e:
        log.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_jam()
