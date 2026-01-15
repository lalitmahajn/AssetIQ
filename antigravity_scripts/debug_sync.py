import sys
import logging
# Configure basic logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

try:
    from apps.plant_worker.sync_agent import push_once
    print("Starting sync push...")
    result = push_once(limit=10)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
