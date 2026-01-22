import os
import sys

# Add the project root to sys.path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

if project_root not in sys.path:
    sys.path.append(project_root)

from apps.plant_backend.models import SystemConfig
from common_core.db import PlantSessionLocal


def check_config():
    try:
        db = PlantSessionLocal()
        try:
            row = db.get(SystemConfig, "whatsappTargetPhone")
            if row:
                print("RESULT_START")
                print(f"Current Value in DB: '{row.config_value}'")
                print("RESULT_END")
            else:
                print("RESULT_START")
                print("WhatsApp Target Phone is NOT set.")
                print("RESULT_END")
        finally:
            db.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_config()
