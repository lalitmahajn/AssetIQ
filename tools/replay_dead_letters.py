from __future__ import annotations
import os, json
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from common_core.db import HQSessionLocal
from apps.hq_backend.hq_backend.models import DeadLetter
from apps.hq_backend.hq_backend.routers.receiver import apply_payload_idempotent
from apps.hq_backend.hq_backend.schema_validate import validate_entity

DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
MAX_BATCH = int(os.environ.get("MAX_BATCH", "200"))

def main():
    db: Session = HQSessionLocal()
    try:
        rows = db.execute(select(DeadLetter).order_by(DeadLetter.created_at_utc.asc()).limit(MAX_BATCH)).scalars().all()
        ok = 0
        fail = 0
        for dl in rows:
            try:
                payload = json.loads(dl.payload_json)
                validate_entity(dl.entity_type, payload)
                apply_payload_idempotent(db, dl.site_code, dl.entity_type, payload, dl.correlation_id)
                ok += 1
                if not DRY_RUN:
                    db.execute(delete(DeadLetter).where(DeadLetter.id == dl.id))
            except Exception as e:
                fail += 1
                dl.error = f"REPLAY_FAIL: {str(e)[:250]}"
        if DRY_RUN:
            db.rollback()
            print(f"DRY_RUN ok={ok} fail={fail}")
        else:
            db.commit()
            print(f"COMMIT ok={ok} fail={fail}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
