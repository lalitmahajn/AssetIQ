from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from apps.plant_backend.deps import require_perm
from apps.plant_backend.models import Ticket, TicketActivity, User
from apps.plant_backend.services import acknowledge_ticket, close_ticket, create_ticket
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/ui/tickets", tags=["ui-tickets"])


def _sla_state(t: Ticket) -> str:
    if t.status == "CLOSED":
        return "CLOSED"
    if not t.sla_due_at_utc:
        return "NO_SLA"
    now = datetime.now(UTC).replace(tzinfo=None)
    if now > t.sla_due_at_utc:
        return "BREACH"
    total = (t.sla_due_at_utc - t.created_at_utc).total_seconds() if t.created_at_utc else 0
    rem = (t.sla_due_at_utc - now).total_seconds()
    if total > 0 and rem / total <= 0.2:
        return "WARN"
    return "OK"


@router.get("/list")
def list_tickets(
    status: str = "OPEN",
    limit: int = 50,
    offset: int = 0,
    user: Annotated[dict, Depends(require_perm("ticket.view"))] = None,
):
    db = PlantSessionLocal()
    try:
        q = (
            select(Ticket, User.full_name)
            .outerjoin(User, Ticket.assigned_to_user_id == User.id)
            .order_by(Ticket.created_at_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        if status.upper() == "OPEN":
            q = q.where(Ticket.status != "CLOSED")
        elif status.upper() == "CLOSED":
            q = q.where(Ticket.status == "CLOSED")

        rows = db.execute(q).all()
        items = [
            {
                "id": t.id,
                "site_code": t.site_code,
                "asset_id": t.asset_id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assigned_to": full_name or t.assigned_to_user_id,
                "source": t.source,
                "created_at_utc": t.created_at_utc.isoformat() + "Z",
                "sla_due_at_utc": t.sla_due_at_utc.isoformat() + "Z" if t.sla_due_at_utc else None,
                "sla_state": _sla_state(t),
                "assigned_dept": t.assigned_dept,
            }
            for t, full_name in rows
        ]
        return {"items": items, "page": {"limit": limit, "offset": offset, "returned": len(items)}}
    finally:
        db.close()


@router.post("/create")
def create(body: dict, user: Annotated[dict, Depends(require_perm("ticket.create"))] = None):
    title = body.get("title", "")
    asset_id = body.get("asset_id", "")
    priority = body.get("priority", "MEDIUM")
    dept = body.get("dept")
    if not title or not asset_id:
        raise HTTPException(status_code=400, detail="title and asset_id required")
    db = PlantSessionLocal()
    try:
        current_username = user.get("sub", "admin")
        # Auto-assign manual tickets to creator
        t = create_ticket(
            db,
            title=title,
            asset_id=asset_id,
            priority=priority,
            source="MANUAL",
            actor_id=current_username,
            assigned_to=current_username,
            dept=dept,
        )
        db.commit()
        return {"ok": True, "id": t.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()


@router.post("/close")
def close(body: dict, user: Annotated[dict, Depends(require_perm("ticket.close"))] = None):
    ticket_id = body.get("ticket_id", "")
    close_note = body.get("close_note", "Closed")
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticket_id required")
    db = PlantSessionLocal()
    try:
        # Use close_note as reason if not provided separately, or add reason field to body
        resolution_reason = body.get("resolution_reason")
        t = close_ticket(
            db,
            ticket_id=ticket_id,
            close_note=close_note,
            resolution_reason=resolution_reason,
            actor_id=None,
        )
        db.commit()
        return {"ok": True, "id": t.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()


@router.post("/assign")
def assign(
    body: dict, user: Annotated[dict, Depends(require_perm("ticket.create"))] = None
):  # Reusing create perm for now or ticket.assign if exists
    ticket_id = body.get("ticket_id")
    username = body.get("username")
    if not ticket_id or not username:
        raise HTTPException(status_code=400, detail="ticket_id and username required")

    db = PlantSessionLocal()
    try:
        from apps.plant_backend.services import assign_ticket

        assign_ticket(db, ticket_id, username)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()


@router.post("/acknowledge")
def acknowledge(
    body: dict, user: Annotated[dict, Depends(require_perm("ticket.create"))] = None
):  # Use create perm or new one
    ticket_id = body.get("ticket_id")
    username = body.get("username", "USER")
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticket_id required")
    db = PlantSessionLocal()
    try:
        t = acknowledge_ticket(
            db, ticket_id, actor_user_id=username, request_id=None
        )  # Pass username as actor
        db.commit()
        return {"ok": True, "status": t.status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()


@router.get("/{ticket_id}/details")
def get_details(ticket_id: str, user: Annotated[dict, Depends(require_perm("ticket.view"))] = None):
    db = PlantSessionLocal()
    try:
        t = db.get(Ticket, ticket_id)
        if not t:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Get activities
        acts = (
            db.execute(
                select(TicketActivity)
                .where(TicketActivity.ticket_id == ticket_id)
                .order_by(TicketActivity.created_at_utc.desc())
            )
            .scalars()
            .all()
        )

        return {
            "ticket": {
                "id": t.id,
                "site_code": t.site_code,
                "asset_id": t.asset_id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assigned_to": t.assigned_to_user_id,
                "source": t.source,
                "stop_id": t.stop_id,
                "created_at_utc": t.created_at_utc.isoformat() + "Z",
                "sla_due_at_utc": t.sla_due_at_utc.isoformat() + "Z" if t.sla_due_at_utc else None,
                "resolution_reason": t.resolution_reason,
            },
            "activity": [
                {
                    "id": a.id,
                    "type": a.activity_type,
                    "actor": a.actor_id,
                    "details": a.details,
                    "created_at_utc": a.created_at_utc.isoformat() + "Z",
                }
                for a in acts
            ],
        }
    finally:
        db.close()
