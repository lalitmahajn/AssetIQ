
import sys
import logging
from datetime import datetime
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO)

try:
    from common_core.db import HQSessionLocal
    from apps.hq_backend.models import RollupDaily, StopReasonDaily
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def debug_hq_data():
    db = HQSessionLocal()
    try:
        today = datetime.utcnow().date().isoformat()
        print(f"Checking data for UTC Day: {today}")

        print("\n--- ROLLUP DAILY ---")
        rollups = db.execute(select(RollupDaily).where(RollupDaily.day_utc == today)).scalars().all()
        if not rollups:
            print("No RollupDaily found.")
        for r in rollups:
            print(f"Site={r.site_code} | Downtime={r.downtime_minutes} min | Stops={r.stops}")

        print("\n--- STOP REASON DAILY ---")
        reasons = db.execute(select(StopReasonDaily).where(StopReasonDaily.day_utc == today)).scalars().all()
        if not reasons:
            print("No StopReasonDaily found.")
        for r in reasons:
            print(f"Site={r.site_code} | Reason={r.reason_code} | Downtime={r.downtime_minutes} min | Stops={r.stops}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_hq_data()
