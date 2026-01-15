import logging
from common_core.db import PlantSessionLocal
from apps.plant_backend.services import create_ticket

logging.basicConfig(level=logging.INFO)

def main():
    db = PlantSessionLocal()
    try:
        logging.info("Creating a test ticket...")
        # Create a ticket
        ticket = create_ticket(
            db=db,
            title="Test Sync Ticket from Antigravity",
            asset_id="Asset-001",
            priority="HIGH"
        )
        db.commit()
        # id is the ticket id
        logging.info(f"Ticket created: {ticket.id}")
    except Exception as e:
        logging.error(f"Failed to create ticket: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
