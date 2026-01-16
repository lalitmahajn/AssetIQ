from __future__ import annotations
import os
import sys

# Ensure we can import from the project root
sys.path.append(os.getcwd())

from common_core.db import HQSessionLocal
from apps.hq_backend.models import (
    AppliedCorrelation, DeadLetter, RollupDaily, TicketSnapshot, 
    TimelineEventHQ, StopReasonDaily, EmailQueue, ReportJob, 
    InsightDaily, PlantRegistry
)

def clean_hq():
    db = HQSessionLocal()
    print("Clearing HQ simulation data...")
    
    try:
        db.query(AppliedCorrelation).delete()
        db.query(DeadLetter).delete()
        db.query(RollupDaily).delete()
        db.query(TicketSnapshot).delete()
        db.query(TimelineEventHQ).delete()
        db.query(StopReasonDaily).delete()
        db.query(EmailQueue).delete()
        db.query(ReportJob).delete()
        db.query(InsightDaily).delete()
        db.query(PlantRegistry).delete()
        
        db.commit()
        print("SUCCESS: HQ data cleared.")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR during HQ cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # This script is usually called by a wrapper, but can be run directly
    clean_hq()
