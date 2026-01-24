"""
Seed Script for Dynamic Masters & Self-Learning
===============================================
Populates the Admin > Master Management tabs.
"""

import os
import sys
import random
from datetime import datetime

sys.path.append(os.getcwd())
from common_core.db import PlantSessionLocal
from apps.plant_backend import models, services

from common_core.config import settings

SITE_CODE = settings.plant_site_code or "P01"
ACTOR_ID = "system_seed"


def seed_dynamic_masters(db):
    print(">> Seeding Dynamic Masters...")
    # Create a new Master Type: "DEPARTMENT"
    type_code = "DEPARTMENT"
    mt = db.query(models.MasterType).filter_by(type_code=type_code).first()
    if not mt:
        mt = models.MasterType(
            site_code=SITE_CODE,
            type_code=type_code,
            name="Departments",
            description="Plant Departments for Ticket Assignment",
            created_at_utc=datetime.utcnow(),
        )
        db.add(mt)
        db.flush()

    # Add Items
    depts = ["Mechanical Maint", "Electrical Maint", "Process Engineering", "Quality Control"]
    for d in depts:
        code = d.upper().replace(" ", "_")
        exists = (
            db.query(models.MasterItem)
            .filter_by(master_type_code=type_code, item_code=code)
            .first()
        )
        if not exists:
            services.master_item_create(db, type_code, code, d, actor_id=ACTOR_ID)
    db.commit()
    print("   Created 'Departments' master list.")


def seed_self_learning(db):
    print(">> Seeding Self-Learning Suggestions...")
    # Simulate recurring "unknown" reasons that operators have typed
    suggestions = [
        ("Conveyor Belt Slip", 12),  # High frequency -> Should be auto-promoted or high priority
        ("HMI Screen Frozen", 4),  # Medium frequency
        ("Bird in Warehouse", 1),  # Low frequency noise
        ("Forklift Battery Dead", 8),
    ]

    for text, count in suggestions:
        key = text.lower().replace(" ", "_")
        exists = db.query(models.ReasonSuggestion).filter_by(normalized_key=key).first()
        if not exists:
            # Create a suggestion entry
            sugg = models.ReasonSuggestion(
                site_code=SITE_CODE,
                master_type_code="STOP_REASON",
                suggested_name=text,
                normalized_key=key,
                count=count,
                status="pending",
                threshold=5,
                last_examples_json=["Operator note: " + text],
                created_at_utc=datetime.utcnow(),
            )
            db.add(sugg)
    db.commit()
    print(f"   Injected {len(suggestions)} suggestions for review.")


if __name__ == "__main__":
    db = PlantSessionLocal()
    try:
        seed_dynamic_masters(db)
        seed_self_learning(db)
        print("\n✅ Admin Features Populated!")
    finally:
        db.close()
