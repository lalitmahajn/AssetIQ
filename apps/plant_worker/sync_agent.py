from __future__ import annotations

import json
import hmac
import hashlib
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select

from common_core.config import settings
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import EventOutbox, DeadLetter, EmailQueue

log = logging.getLogger("assetiq.sync_agent")
MAX_RETRIES = 10

def _now() -> datetime:
    return datetime.utcnow()

def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

def _next_backoff(retry_count: int) -> datetime:
    secs = min(600, 5 * (2 ** max(0, retry_count)))
    return _now() + timedelta(seconds=secs)

def push_once(batch: int = 200) -> dict:
    db = PlantSessionLocal()
    try:
        rows = db.execute(
            select(EventOutbox)
            .where(EventOutbox.sent_at_utc.is_(None))
            .where((EventOutbox.next_attempt_at_utc.is_(None)) | (EventOutbox.next_attempt_at_utc <= _now()))
            .order_by(EventOutbox.created_at_utc.asc())
            .limit(batch)
        ).scalars().all()

        if not rows:
            return {"sent": 0}

        items = [{"site_code": r.site_code, "entity_type": r.entity_type, "entity_id": r.entity_id, "payload": r.payload_json, "correlation_id": r.correlation_id} for r in rows]
        body = json.dumps({"items": items}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-Signature": _sign(body, settings.sync_hmac_secret), "X-Kid": settings.sync_hmac_kid}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(settings.hq_receiver_url, content=body, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            err = str(e)[:300]
            now = _now()
            for r in rows:
                r.retry_count = int(r.retry_count or 0) + 1
                r.last_error = err
                if r.retry_count >= MAX_RETRIES:
                    db.add(DeadLetter(site_code=r.site_code, entity_type=r.entity_type, correlation_id=r.correlation_id, payload_json=json.dumps(r.payload_json), error=err, created_at_utc=now))
                    db.add(EmailQueue(to_email=settings.email_it, subject=f"[{settings.plant_site_code}] SYNC DEAD-LETTER {r.correlation_id}", body=f"Outbox moved to dead-letter. Correlation={r.correlation_id} Error={err}", status="PENDING", created_at_utc=now, sent_at_utc=None))
                    r.sent_at_utc = now
                else:
                    r.next_attempt_at_utc = _next_backoff(r.retry_count)
            db.commit()
            raise

        now = _now()
        for r in rows:
            r.sent_at_utc = now
            r.last_error = None
            r.next_attempt_at_utc = None
        db.commit()
        return {"sent": len(rows)}
    finally:
        db.close()
