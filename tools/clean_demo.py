from __future__ import annotations
import os
import sys

# Ensure we can import from the project root
sys.path.append(os.getcwd())

from common_core.db import PlantSessionLocal
from apps.plant_backend.models import Asset, MasterType, MasterItem, StopQueue, Ticket, TicketActivity, TimelineEvent, AuditLog, ReportRequest, EventOutbox, EmailQueue

def clean():
    db = PlantSessionLocal()
    print("Clearing simulation data...")
    
    try:
        # Delete in order of potential dependencies (though they are soft in this app)
        db.query(TicketActivity).delete()
        db.query(Ticket).delete()
        db.query(StopQueue).delete()
        db.query(TimelineEvent).delete()
        db.query(AuditLog).delete()
        db.query(ReportRequest).delete()
        db.query(EventOutbox).delete()
        db.query(EmailQueue).delete()
        
        # Optional: Clear assets and masters for a totally fresh start
        db.query(MasterItem).delete()
        db.query(MasterType).delete()
        db.query(Asset).delete()
        
        db.commit()
        print("\nSUCCESS: All data cleared. Your database is now fresh.")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if "--no-prompt" in sys.argv:
        clean()
    else:
        confirm = input("This will DELETE ALL data from the plant database. Are you sure? (y/n): ")
        if confirm.lower() == 'y':
            clean()
        else:
            print("Cleanup cancelled.")
