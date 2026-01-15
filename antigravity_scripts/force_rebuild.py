
import sys
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("force_rebuild")

try:
    from apps.hq_worker.worker import _rebuild_stop_reason_daily
    from apps.hq_backend.intelligence import recompute_and_store_daily_insights
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

if __name__ == "__main__":
    # Rebuild for Jan 09 (Yesterday) and Jan 10 (Today, to be safe)
    # The worker usually only does yesterday.
    
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    days = [yesterday.isoformat(), today.isoformat()]
    
    for d in days:
        log.info(f"Rebuilding aggregates for {d}...")
        n = _rebuild_stop_reason_daily(d)
        log.info(f"  -> Updated {n} rows.")
        
        log.info(f"Recalculating insights for {d}...")
        c = recompute_and_store_daily_insights(d)
        log.info(f"  -> Generated {c} insights.")

    log.info("Force rebuild complete.")
