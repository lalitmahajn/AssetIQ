import sys
from datetime import datetime, timedelta
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, Ticket
from apps.plant_backend.services import _new_id, _now

db = PlantSessionLocal()
try:
    print("Seeding Insight Data...")
    now = datetime.utcnow()
    
    # 1. Seed Repeated Stop Pattern: "Jam" happens 5 times over last 3 days
    for day_offset in [0, 1, 2]:
        day = now - timedelta(days=day_offset)
        # 2 stops per day
        for i in range(2):
            stop_id = _new_id("STOP")
            db.add(StopQueue(
                id=stop_id,
                site_code="P01",
                asset_id="CONVEYOR-01",
                reason="Jam",
                is_open=False,
                opened_at_utc=day,
                closed_at_utc=day + timedelta(minutes=10)
            ))
            
    # 2. Seed SLA Breach Trend
    # 5 breaches today
    for i in range(5):
        tid = _new_id("TCK")
        created = now - timedelta(hours=5)
        sla_due = now - timedelta(hours=1) # Already past
        db.add(Ticket(
             id=tid,
             site_code="P01",
             asset_id="MOTOR-01",
             title="SLA Breach Test",
             status="OPEN",
             priority="HIGH",
             created_at_utc=created,
             sla_due_at_utc=sla_due,
             acknowledged_at_utc=None
        ))
        
    db.commit()
    print("Seeding Complete.")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
