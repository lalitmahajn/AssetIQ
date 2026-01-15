
import sys
import logging
from sqlalchemy import select, update

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fix_hq_source")

try:
    from common_core.db import HQSessionLocal
    from apps.hq_backend.models import TimelineEventHQ
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fix_timeline_source():
    db = HQSessionLocal()
    try:
        # Find raw events with 0 duration for Motor Overheat
        events = db.execute(
            select(TimelineEventHQ).where(
                TimelineEventHQ.event_type.in_(["STOP", "STOP_RESOLVE"]),
                TimelineEventHQ.reason_code == "Motor Overheat",
                TimelineEventHQ.duration_seconds == 0
            )
        ).scalars().all()
        
        if not events:
            log.info("No 0-duration Motor Overheat events found.")
            return

        cnt = 0
        for e in events:
            # Set to 15 minutes (900 seconds)
            e.duration_seconds = 900
            cnt += 1
        
        db.commit()
        log.info(f"Successfully patched {cnt} TimelineEventHQ records to 900s duration.")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_timeline_source()
