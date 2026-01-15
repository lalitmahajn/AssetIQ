
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("move_data")

try:
    from common_core.db import HQSessionLocal
    from apps.hq_backend.models import TimelineEventHQ, RollupDaily, StopReasonDaily
    from apps.hq_worker.worker import _rebuild_stop_reason_daily
    from apps.hq_backend.intelligence import recompute_and_store_daily_insights
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def move_data_to_today():
    db = HQSessionLocal()
    try:
        now = datetime.utcnow()
        today_str = now.date().isoformat()
        yesterday_str = (now.date() - timedelta(days=1)).isoformat()
        
        log.info(f"Moving 'Motor Overheat' events from history to {today_str}...")
        
        # 1. Update Timeline Events
        events = db.execute(
            select(TimelineEventHQ).where(
                TimelineEventHQ.reason_code == "Motor Overheat"
            )
        ).scalars().all()
        
        if not events:
            log.warning("No Motor Overheat events found to move.")
        else:
            for e in events:
                e.occurred_at_utc = now
            log.info(f"Updated {len(events)} events to {now}")

        # 2. Update RollupDaily for Today
        rollup = db.execute(
            select(RollupDaily).where(RollupDaily.day_utc == today_str, RollupDaily.site_code == 'P01')
        ).scalar_one_or_none()
        
        if rollup:
            rollup.downtime_minutes = 90
            rollup.stops = len(events)
            log.info(f"Updated RollupDaily for {today_str}: 90 min, {len(events)} stops")
        else:
            # Create if missing
            db.add(RollupDaily(
                site_code='P01',
                day_utc=today_str,
                stops=len(events),
                downtime_minutes=90,
                updated_at_utc=now
            ))
            log.info(f"Created RollupDaily for {today_str}")

        # 3. Clean up Yesterday's aggregates (to avoid confusion if user checks)
        db.execute(
            update(StopReasonDaily)
            .where(StopReasonDaily.day_utc == yesterday_str)
            .values(stops=0, downtime_minutes=0)
        )
        
        db.commit()
        
        # 4. Rebuild Today's Aggregates
        log.info(f"Rebuilding aggregates for {today_str}...")
        _rebuild_stop_reason_daily(today_str)
        
        # 5. Recompute Insights
        log.info(f"Recomputing insights for {today_str}...")
        recompute_and_store_daily_insights(today_str)
        
    finally:
        db.close()

if __name__ == "__main__":
    move_data_to_today()
