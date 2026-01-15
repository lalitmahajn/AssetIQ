from __future__ import annotations
import logging
from datetime import datetime
from sqlalchemy import select
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import EmailQueue

log = logging.getLogger("assetiq.email")

def send_pending(limit: int = 50) -> int:
    db = PlantSessionLocal()
    sent = 0
    try:
        rows = db.execute(
            select(EmailQueue).where(EmailQueue.status=="PENDING").order_by(EmailQueue.created_at_utc.asc()).limit(limit)
        ).scalars().all()

        for e in rows:
            e.status = "SENT"
            e.sent_at_utc = datetime.utcnow()
            sent += 1
            log.info("email_marked_sent", extra={"component":"plant_worker"})
        db.commit()
        return sent
    finally:
        db.close()
