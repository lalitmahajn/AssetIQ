from __future__ import annotations
import logging
from common_core.db import PlantSessionLocal
from apps.plant_backend import services

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test_auto")

def run_test():
    db = PlantSessionLocal()
    try:
        log.info("Opening STOP for TEST-AUTO-01...")
        res = services.open_stop(
            db, 
            asset_id="TEST-AUTO-01", 
            reason="Simulated PLC Fault (Overpressure)", 
            actor_user_id="sim_plc", 
            actor_station_code="PLC-01", 
            request_id="TEST-001"
        )
        db.commit()
        log.info(f"Stop Opened. Result: {res}")
        log.info("Check Ticket List for a new High Priority ticket!")
    except Exception as e:
        log.error(f"Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
