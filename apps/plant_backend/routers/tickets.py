from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.plant_backend.security_deps import require_roles
from apps.plant_backend.services import acknowledge_ticket
from common_core.db import PlantSessionLocal

log = logging.getLogger("assetiq.tickets")
router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/{ticket_id}/ack")
def ack(
    ticket_id: str,
    request: Request,
    claims: Annotated[Any, Depends(require_roles("maintenance", "supervisor", "admin"))] = None,
):
    db = PlantSessionLocal()
    try:
        t = acknowledge_ticket(
            db, ticket_id, claims.get("sub"), getattr(request.state, "request_id", None)
        )
        db.commit()
        return {
            "ok": True,
            "ticket_id": t.id,
            "acknowledged_at_utc": (t.acknowledged_at_utc.isoformat() + "Z")
            if t.acknowledged_at_utc
            else None,
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        log.exception("ticket_ack_failed")
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()
