
from sqlalchemy import text
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import Base, TicketActivity

def migrate():
    db = PlantSessionLocal()
    # 1. Create ticket_activities table if not exists
    print("Checking TicketActivity table...")
    engine = db.get_bind()
    Base.metadata.create_all(engine) # Should create new tables

    # 2. Add columns to tickets table if missing
    print("Checking Ticket columns...")
    try:
        db.execute(text("ALTER TABLE tickets ADD COLUMN source VARCHAR(32) DEFAULT 'MANUAL'"))
        print("Added source column")
    except Exception as e:
        print(f"Skipping source: {e}")
        db.rollback()

    try:
        db.execute(text("ALTER TABLE tickets ADD COLUMN stop_id VARCHAR(64)"))
        db.execute(text("CREATE INDEX ix_tickets_stop_id ON tickets (stop_id)"))
        print("Added stop_id column")
    except Exception as e:
        print(f"Skipping stop_id: {e}")
        db.rollback()

    try:
        db.execute(text("ALTER TABLE tickets ADD COLUMN resolution_reason VARCHAR(64)"))
        print("Added resolution_reason column")
    except Exception as e:
        print(f"Skipping resolution_reason: {e}")
        db.rollback()

    db.commit()
    db.close()

if __name__ == "__main__":
    migrate()
