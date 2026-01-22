from sqlalchemy import text

from common_core.db import PlantSessionLocal


def migrate():
    db = PlantSessionLocal()
    try:
        print("Migrating tickets table to add sla_breach_sent...")
        try:
            db.execute(text("SELECT sla_breach_sent FROM tickets LIMIT 1"))
            print("Column 'sla_breach_sent' already exists.")
        except Exception:
            print("Column missing. Adding 'sla_breach_sent'...")
            db.rollback()
            db.execute(
                text(
                    "ALTER TABLE tickets ADD COLUMN sla_breach_sent BOOLEAN DEFAULT FALSE NOT NULL"
                )
            )
            db.commit()
            print("Added 'sla_breach_sent' successfully.")
    except Exception as e:
        print(f"Migration Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
