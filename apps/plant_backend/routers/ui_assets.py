from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import TimelineEvent
from apps.plant_backend.deps import require_perm

router = APIRouter(prefix="/ui/assets", tags=["ui-assets"])

@router.get("/{asset_id}/history")
def get_asset_history(asset_id: str, limit: int = 10, user=Depends(require_perm("ticket.view"))):
    db = PlantSessionLocal()
    try:
        # Fetch events for this asset (STOP, TICKET, etc.)
        q = select(TimelineEvent)\
            .where(TimelineEvent.asset_id == asset_id)\
            .order_by(TimelineEvent.occurred_at_utc.desc())\
            .limit(limit)
            
        events = db.execute(q).scalars().all()
        
        return [{
            "id": e.id,
            "type": e.event_type,
            "occurred_at": e.occurred_at_utc.isoformat(),
            "payload": e.payload_json
        } for e in events]
    finally:
        db.close()
