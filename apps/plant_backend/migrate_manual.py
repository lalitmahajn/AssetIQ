from sqlalchemy import text

from common_core.db import PlantSessionLocal


def migrate():
    db = PlantSessionLocal()
    try:
        print("Checking/Adding attributes to StopQueue...")
        # Check if column exists
        try:
            db.execute(text("SELECT live_context_json FROM stop_queue LIMIT 1"))
            print("Column 'live_context_json' already exists.")
        except Exception:
            print("Column missing. Adding 'live_context_json'...")
            db.rollback()  # Clear error
            db.execute(text("ALTER TABLE stop_queue ADD COLUMN live_context_json JSON"))
            db.commit()
            print("Added 'live_context_json' successfully.")

        # Also create PLC tables if they don't exist (just in case create_all failed silently)
        # Though /plc/configs 200 OK suggests they exist.

    except Exception as e:
        print(f"Migration Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
