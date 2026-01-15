import sys
import logging
# Configure basic logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

try:
    from apps.plant_worker.rollup_agent import compute_rollup_once
    print("Starting rollup computation...")
    result = compute_rollup_once()
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
