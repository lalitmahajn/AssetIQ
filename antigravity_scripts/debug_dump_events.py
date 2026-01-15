import sys
from sqlalchemy import select
from common_core.db import HQSessionLocal
from apps.hq_backend.models import TimelineEventHQ

def dump():
    db = HQSessionLocal()
    print("--- TimelineEventHQ Dump ---")
    rows = db.execute(select(TimelineEventHQ).limit(20)).scalars().all()
    for r in rows:
        print(f"ID={r.id} Site={r.site_code} Type={r.event_type} Reason={r.reason_code} Time={r.occurred_at_utc}")
    print("----------------------------")
    if not rows:
        print("(No events found)")
    
if __name__ == "__main__":
    dump()
