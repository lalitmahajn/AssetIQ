
import sys
import logging
from datetime import datetime
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import StopQueue
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def debug_plant_data():
    db = PlantSessionLocal()
    try:
        print("\n--- RAW STOP QUEUE (PLANT) ---")
        stops = db.execute(select(StopQueue).order_by(StopQueue.opened_at_utc.desc()).limit(10)).scalars().all()
        if not stops:
            print("No stops found in StopQueue.")
        for s in stops:
            duration = "OPEN"
            if s.closed_at_utc:
                duration = f"{(s.closed_at_utc - s.opened_at_utc).total_seconds() / 60:.2f} min"
            print(f"ID={s.id} | Reason={s.reason} | Open={s.opened_at_utc} | Closed={s.closed_at_utc} | Duration={duration}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_plant_data()
