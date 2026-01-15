
import logging
from datetime import datetime, timedelta
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import Asset, TimelineEvent, Ticket
import uuid

def simulate():
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        site_code = "P01"
        asset_id = "LINE-1"
        
        # 1. Ensure Asset
        if not db.get(Asset, asset_id):
            db.add(Asset(id=asset_id, site_code=site_code, name="Line 1", asset_type="LINE", created_at_utc=now))
            print("Created Asset LINE-1")
            
        # 2. Create Events (Stops)
        # Stop 1: 30 mins ago, lasted 15 mins
        start1 = now - timedelta(minutes=30)
        stop1_id = str(uuid.uuid4())
        db.add(TimelineEvent(
            id=stop1_id,
            site_code=site_code,
            asset_id=asset_id,
            event_type="STOP",
            payload_json={"duration_seconds": 900, "reason_code": "JAM"},
            occurred_at_utc=start1,
            correlation_id=f"sim:{stop1_id}",
            created_at_utc=now
        ))
        
        # Stop 2: 2 hours ago, lasted 45 mins
        start2 = now - timedelta(hours=2)
        stop2_id = str(uuid.uuid4())
        db.add(TimelineEvent(
            id=stop2_id,
            site_code=site_code,
            asset_id=asset_id,
            event_type="STOP",
            payload_json={"duration_seconds": 2700, "reason_code": "NO_MATERIAL"},
            occurred_at_utc=start2,
            correlation_id=f"sim:{stop2_id}",
            created_at_utc=now
        ))
        print("Created 2 Stops")
        
        # 3. Create Tickets
        # Ticket 1: Closed
        t1_id = str(uuid.uuid4())
        db.add(Ticket(
            id=t1_id,
            site_code=site_code,
            asset_id=asset_id,
            title="Conveyor noise",
            status="CLOSED",
            priority="LOW",
            created_at_utc=now - timedelta(hours=3),
            resolved_at_utc=now - timedelta(hours=1),
            close_note="Lubricated chain"
        ))
        
        # Ticket 2: Open
        t2_id = str(uuid.uuid4())
        db.add(Ticket(
            id=t2_id,
            site_code=site_code,
            asset_id=asset_id,
            title="Sensor calibration needed",
            status="OPEN",
            priority="HIGH",
            created_at_utc=now - timedelta(minutes=10)
        ))
        print("Created 2 Tickets")
        
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate()
