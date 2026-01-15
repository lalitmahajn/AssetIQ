
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue
from sqlalchemy import select

def check():
    db = PlantSessionLocal()
    try:
        stops = db.execute(select(StopQueue)).scalars().all()
        print(f"Total stops in DB: {len(stops)}")
        for s in stops:
            print(f"Stop: {s.id}, Asset: {s.asset_id}, Open: {s.is_open}, Reason: {s.reason}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
