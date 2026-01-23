import datetime
import os
import random
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid

from apps.plant_backend.models import Asset, StopQueue
from common_core.config import settings


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# Setup DB
DATABASE_URL = settings.plant_db_url
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()


def create_simulated_stops():
    print("Simulating repeated stops to trigger insight...")

    # Use an existing asset or find one
    asset = db.execute(select(Asset)).scalars().first()
    if not asset:
        print("No assets found. Create an asset first.")
        return

    asset_id = asset.id
    reason_code = "Motor Overheating"

    # We need 5+ stops across 3+ days
    now = datetime.datetime.utcnow()

    # Day 1: 2 stops
    day1 = now - datetime.timedelta(days=3)
    # Day 2: 2 stops
    day2 = now - datetime.timedelta(days=2)
    # Day 3: 2 stops
    day3 = now - datetime.timedelta(days=1)

    days = [day1, day2, day3]

    count = 0
    for d in days:
        for _ in range(2):
            stop_id = _new_id("STP")
            opened_at = d + datetime.timedelta(hours=random.randint(8, 16))
            closed_at = opened_at + datetime.timedelta(
                minutes=random.randint(30, 90)
            )  # Long enough to cause downtime

            sq = StopQueue(
                id=stop_id,
                site_code=settings.plant_site_code,
                asset_id=asset_id,
                reason=reason_code,
                is_open=False,
                opened_at_utc=opened_at,
                closed_at_utc=closed_at,
                resolution_text="Cooled down motor",
                live_context_json={},
            )
            db.add(sq)
            count += 1
            print(f"Created Stop: {stop_id} on {opened_at.date()} for {reason_code}")

    db.commit()
    print(f"Successfully created {count} simulated stops for {asset_id}.")


if __name__ == "__main__":
    try:
        create_simulated_stops()
    finally:
        db.close()
