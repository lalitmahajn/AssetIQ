import sys
from datetime import datetime
from common_core.config import settings
from apps.hq_backend.intelligence import recompute_and_store_daily_insights

def run():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Forcing insight recomputation for TODAY: {today}...")
    try:
        count = recompute_and_store_daily_insights(today, window_days=settings.intelligence_window_days)
        print(f"Success! Generated {count} insights.")
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
