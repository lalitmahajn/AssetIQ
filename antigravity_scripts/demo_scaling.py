
from datetime import datetime
from common_core.db import HQSessionLocal
from apps.hq_backend.models import RollupDaily, PlantRegistry

db = HQSessionLocal()
try:
    day = datetime.utcnow().date().isoformat()
    print(f"Injecting dummy data for day: {day}")

    # Ensure P02 exists in registry
    p2 = db.query(PlantRegistry).filter_by(site_code="P02").first()
    if not p2:
        p2 = PlantRegistry(
            site_code="P02",
            display_name="Plant 2 (Demo)",
            is_active=True,
            last_seen_at_utc=datetime.utcnow()
        )
        db.add(p2)
        print("Created P02 in registry")

    # Upsert Rollup for P02 with 30 mins downtime (half of P01's likely 60)
    rollup = db.query(RollupDaily).filter_by(site_code="P02", day_utc=day).first()
    if not rollup:
        rollup = RollupDaily(
            site_code="P02",
            day_utc=day,
            downtime_minutes=30,  # 30 mins
            stops=5,
            sla_breaches=0,
            tickets_open=1,
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow()
        )
        db.add(rollup)
        print("Created P02 rollup (30 mins)")
    else:
        rollup.downtime_minutes = 30
        rollup.updated_at_utc = datetime.utcnow()
        print("Updated P02 rollup to 30 mins")

    db.commit()
    print("Done. Refresh the UI.")
finally:
    db.close()
