import sys
import logging
from datetime import datetime

# Setup logging to stdout
logging.basicConfig(level=logging.INFO)

from apps.hq_worker.worker import _rebuild_stop_reason_daily
from apps.hq_backend.intelligence import recompute_and_store_daily_insights
from common_core.config import settings

def run():
    # Force calculation for TODAY (since simulation data is for today)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"--- Full Recalc for {today} ---")
    
    print("1. Re-Aggregating Stop Reasons (populate StopReasonDaily)...")
    try:
        n = _rebuild_stop_reason_daily(today)
        print(f"   > Aggregated {n} entries.")
    except Exception as e:
        print(f"   > Aggregation Failed: {e}")
        import traceback
        traceback.print_exc()

    print("2. Re-Computing Insights (populate InsightDaily)...")
    try:
        n_ins = recompute_and_store_daily_insights(today, window_days=settings.intelligence_window_days)
        print(f"   > Generated {n_ins} insights.")
    except Exception as e:
        print(f"   > Intelligence Failed: {e}")
        import traceback
        traceback.print_exc()

    print("--- Done ---")

if __name__ == "__main__":
    run()
