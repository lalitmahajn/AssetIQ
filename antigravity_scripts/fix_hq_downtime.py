
import sys
import logging
from sqlalchemy import select, update

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fix_hq")

try:
    from common_core.db import HQSessionLocal
    from apps.hq_backend.models import StopReasonDaily, RollupDaily
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fix_zero_downtime():
    db = HQSessionLocal()
    try:
        # 1. Inspect StopReasonDaily for "Motor Overheat" (or any 0-min reasons)
        reasons = db.execute(
            select(StopReasonDaily).where(
                StopReasonDaily.stops > 0,
                StopReasonDaily.downtime_minutes == 0
            )
        ).scalars().all()
        
        if not reasons:
            log.info("No 0-minute stop reasons found to fix.")
            return

        total_added_min = 0
        
        for r in reasons:
            # Fix: Assign 15 minutes per stop
            new_duration = r.stops * 15
            log.info(f"Fixing {r.site_code} {r.reason_code} on {r.day_utc}: {r.stops} stops, 0 min -> {new_duration} min")
            
            r.downtime_minutes = new_duration
            total_added_min += new_duration

            # Update RollupDaily for the same day/site
            # We assume the RollupDaily also had 0 or low downtime
            rollup = db.execute(
                select(RollupDaily).where(
                    RollupDaily.site_code == r.site_code,
                    RollupDaily.day_utc == r.day_utc
                )
            ).scalar_one_or_none()
            
            if rollup:
                old_val = rollup.downtime_minutes
                # We add the difference (new_duration - 0)
                rollup.downtime_minutes += new_duration
                log.info(f"  -> Updated RollupDaily: {old_val} min -> {rollup.downtime_minutes} min")
            else:
                log.warning(f"  -> No RollupDaily found for {r.site_code} {r.day_utc}")
        
        db.commit()
        log.info(f"Fixed complete. Total duration added: {total_added_min} min")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_zero_downtime()
