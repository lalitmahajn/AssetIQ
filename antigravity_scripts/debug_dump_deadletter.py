import sys
from sqlalchemy import select
from common_core.db import HQSessionLocal
from apps.hq_backend.models import DeadLetter

def dump():
    db = HQSessionLocal()
    print("--- DeadLetter Dump ---")
    rows = db.execute(select(DeadLetter).limit(20)).scalars().all()
    for r in rows:
        print(f"ID={r.id} Site={r.site_code} Type={r.entity_type} Err={r.error}")
    print("-----------------------")
    if not rows:
        print("(No dead letters)")

if __name__ == "__main__":
    dump()
