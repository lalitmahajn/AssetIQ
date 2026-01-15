
from apps.plant_worker.rollup_agent import compute_rollup_once
from apps.plant_worker.sync_agent import push_once
import time

print("Triggering Manual Rollup...")
if compute_rollup_once():
    print("Rollup computed.")
else:
    print("Rollup failed or no change.")

print("Triggering Sync Push...")
res = push_once(batch=500)
print(f"Sync Result: {res}")
