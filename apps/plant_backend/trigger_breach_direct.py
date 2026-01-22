import os
import sys

# Add the project root to sys.path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

if project_root not in sys.path:
    sys.path.append(project_root)

from apps.plant_backend.routers.master import simulate_sla_breach


def run():
    print("Triggering simulation directly...")
    try:
        res = simulate_sla_breach(claims=None)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run()
