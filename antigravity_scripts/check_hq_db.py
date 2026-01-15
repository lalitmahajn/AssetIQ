from __future__ import annotations
import logging
from sqlalchemy import select, text
from common_core.db import HQSessionLocal
from apps.hq_backend.models import StopReasonDaily, PlantRegistry, RollupDaily

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("debug_hq")

def check_db():
    db = HQSessionLocal()
    try:
        print("\n--- PLANTS ---")
        plants = db.execute(select(PlantRegistry)).scalars().all()
        for p in plants:
            print(f"Site: {p.site_code} | LastSeen: {p.last_seen_at_utc}")

        print("\n--- ROLLUPS (2026-01-13) ---")
        rollups = db.execute(select(RollupDaily).where(RollupDaily.day_utc == "2026-01-13")).scalars().all()
        for r in rollups:
            print(f"Site: {r.site_code} | Stops: {r.stops} | DT: {r.downtime_minutes}")

        print("\n--- STOP REASONS (2026-01-13) ---")
        reasons = db.execute(select(StopReasonDaily).where(StopReasonDaily.day_utc == "2026-01-13")).scalars().all()
        if not reasons:
            print("NO STOP REASONS FOUND!")
        for sr in reasons:
            print(f"Site: {sr.site_code} | Reason: {sr.reason_code} | Stops: {sr.stops} | DT: {sr.downtime_minutes}")

    finally:
        db.close()

if __name__ == "__main__":
    check_db()
