from fastapi import APIRouter
from sqlalchemy import func, select

from apps.plant_backend.models import EmailQueue, EventOutbox, StopQueue, Ticket
from common_core.db import PlantSessionLocal

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics():
    db = PlantSessionLocal()
    try:
        outbox_pending = db.execute(
            select(func.count()).select_from(EventOutbox).where(EventOutbox.sent_at_utc.is_(None))
        ).scalar_one()
        email_pending = db.execute(
            select(func.count()).select_from(EmailQueue).where(EmailQueue.status == "PENDING")
        ).scalar_one()
        stops_open = db.execute(
            select(func.count()).select_from(StopQueue).where(StopQueue.is_open.is_(True))
        ).scalar_one()
        tickets_open = db.execute(
            select(func.count()).select_from(Ticket).where(Ticket.status != "CLOSED")
        ).scalar_one()
        text = ""
        text += f"assetiq_outbox_pending {outbox_pending}\n"
        text += f"assetiq_email_pending {email_pending}\n"
        text += f"assetiq_stops_open {stops_open}\n"
        text += f"assetiq_tickets_open {tickets_open}\n"
        return text
    finally:
        db.close()
