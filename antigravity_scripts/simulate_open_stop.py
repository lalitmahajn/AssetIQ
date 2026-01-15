
import sys
import logging
from datetime import datetime
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, TimelineEvent
from apps.plant_backend.services import _new_id, _now

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sim_stop")

def simulate():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        import random
        asset = f"CONVEYOR-{random.randint(1,5):02d}"
        from sqlalchemy import select
        from apps.plant_backend.models import ReasonSuggestion
        
        # Try to fetch active reasons from DB
        reasons_db = db.execute(select(ReasonSuggestion).where(ReasonSuggestion.is_active == True)).scalars().all()
        if reasons_db:
             reason = random.choice([r.suggested_name for r in reasons_db])
        else:
             reason = random.choice(["Safety Guard Open", "Emergency Stop Pressed", "Jam at Sensor 3", "Motor Overload"])
        
        stop_id = _new_id("STOP")
        
        log.info(f"Simulating ACTIVE stop on {asset} ({reason})")
        
        # Use service to ensure Ticket, Email, Audit, etc. are created
        from apps.plant_backend.services import open_stop
        
        # open_stop commits internally? No, looking at service it adds to DB.
        # We need to pass the session `db`.
        # open_stop(db, asset_id, reason, actor_user_id, actor_station_code, request_id)
        
        res = open_stop(
            db=db, 
            asset_id=asset, 
            reason=reason, 
            actor_user_id="sim_script", 
            actor_station_code="SIM", 
            request_id="sim_run"
        )
        
        db.commit()
        log.info(f"Simulation complete. Stop {res['stop_id']} OPEN. Ticket {res['ticket_id']} CREATED.")
        log.info("Simulation complete. Stop is OPEN.")
        
    except Exception as e:
        log.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate()
