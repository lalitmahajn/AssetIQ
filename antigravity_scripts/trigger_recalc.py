
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)

try:
    from apps.hq_backend.intelligence import recompute_and_store_daily_insights
except ImportError as e:
    print(f"Error importing intelligence module: {e}")
    sys.exit(1)

if __name__ == "__main__":
    today = datetime.utcnow().date().isoformat()
    logging.info(f"Triggering Insight Recalculation for {today}...")
    
    count = recompute_and_store_daily_insights(today)
    
    logging.info(f"Done. Generated {count} insights.")
