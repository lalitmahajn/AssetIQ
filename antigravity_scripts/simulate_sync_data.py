import sys
import logging
from datetime import datetime, timedelta
from typing import Any

from common_core.db import PlantSessionLocal
from apps.plant_backend import services
from apps.plant_backend.models import StopQueue, Ticket

# Mock request state
class MockRequest:
    state = type("State", (), {"request_id": "SIM-001"})()

def simulate():
    db = PlantSessionLocal()
    try:
        print("Simulating Sync Data (Stops & Tickets)...")
        now = datetime.utcnow()
        
        # 1. Repeated Stop Pattern: "Motor Overheat"
        # 6 times over 3 days
        print("- Creating 'Motor Overheat' stops...")
        for day_offset in [0, 1, 2]:
            for i in range(2):
                res = services.open_stop(
                    db, 
                    asset_id="MOTOR-02", 
                    reason="Motor Overheat", 
                    actor_user_id="sim_user", 
                    actor_station_code="SIM", 
                    request_id="SIM-001"
                )
                db.commit() # Ensure stop is saved before resolving
                stop_id = res["stop_id"]
                # Close it immediately to record duration
                services.resolve_stop(
                    db,
                    stop_id,
                    resolution_text="Cooled down",
                    actor_user_id="sim_user",
                    request_id="SIM-001"
                )
                db.commit()
        
        # 2. SLA Breach Trend
        # 5 High priority tickets created 5 hours ago (default SLA is 4h)
        print("- Creating SLA Breached tickets...")
        for i in range(5):
             # Manually create via service to get Outbox entry
             # But service uses `now` for creation time. 
             # We need to hack the creation time OR just manually create Ticket+Outbox to simulate past events.
             # Using service is better for schema correctness but timestamp is tricky.
             # We will use service then Update the timestamp.
             t = services.create_ticket(
                 db,
                 title=f"Critical Fault {i}",
                 asset_id="PUMP-01",
                 priority="HIGH"
             )
             # Hack: Backdate it
             t.created_at_utc = now - timedelta(hours=5)
             t.sla_due_at_utc = now - timedelta(hours=1)
             # Also need to update the EventOutbox payload to reflect past time?
             # Actually EventOutbox payload `ts` is just for info, keys are what matters. 
             # HQ might use `created_at_utc` from payload.
             # Let's hope HQ uses the DB column `created_at_utc` from the TicketSnapshot.
             
        db.commit()
        print("Simulation Complete. Data queued in EventOutbox.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate()
