import os
import sys

from sqlalchemy import text

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from common_core.db import PlantSessionLocal


def inspect_queue():
    db = PlantSessionLocal()
    try:
        print("--- WHATSAPP QUEUE INSPECTION ---")
        # Get last 5 messages
        rows = db.execute(
            text(
                "SELECT id, status, sla_state, phone_number, created_at_utc FROM whatsapp_queue ORDER BY id DESC LIMIT 5"
            )
        ).fetchall()

        if not rows:
            print("No messages found in queue.")
        else:
            for r in rows:
                print(
                    f"ID: {r.id} | Status: {r.status} | SLA: {r.sla_state} | Targets: {r.phone_number[:50]}..."
                )

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    inspect_queue()
