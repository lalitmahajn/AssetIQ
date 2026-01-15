from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from common_core.config import settings
from apps.plant_backend.models import AuditLog, EmailQueue, StopQueue, Ticket, TimelineEvent, EventOutbox, Asset, TicketActivity, MasterType, MasterItem, ReasonSuggestion, ReportRequest
from sqlalchemy import select


def _now() -> datetime:
    return datetime.utcnow()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:18]}"


def audit_write(db, action: str, entity_type: str, entity_id: str, details: dict[str, Any],
                actor_user_id: str | None, actor_station_code: str | None, request_id: str | None) -> None:
    db.add(AuditLog(
        site_code=settings.plant_site_code,
        actor_user_id=actor_user_id,
        actor_station_code=actor_station_code,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        details_json=details,
        created_at_utc=_now(),
    ))


def timeline_append(db, asset_id: str, event_type: str, payload: dict[str, Any], correlation_id: str) -> str:
    tid = _new_id("TL")
    db.add(TimelineEvent(
        id=tid,
        site_code=settings.plant_site_code,
        asset_id=asset_id,
        event_type=event_type,
        payload_json=payload,
        occurred_at_utc=_now(),
        correlation_id=correlation_id,
        created_at_utc=_now(),
    ))
    return tid


def enqueue_email(db, to_email: str, subject: str, body: str) -> None:
    db.add(EmailQueue(
        to_email=to_email,
        subject=subject,
        body=body,
        status="PENDING",
        created_at_utc=_now(),
        sent_at_utc=None,
    ))


def outbox_add(db, entity_type: str, entity_id: str, payload: dict[str, Any], correlation_id: str) -> None:
    db.add(EventOutbox(
        site_code=settings.plant_site_code,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload,
        correlation_id=correlation_id,
        created_at_utc=_now(),
        sent_at_utc=None,
        retry_count=0,
        next_attempt_at_utc=_now(),
        last_error=None,
    ))


def log_ticket_activity(db, ticket_id: str, activity_type: str, details: str, actor_id: str | None = None) -> None:
    db.add(TicketActivity(
        ticket_id=ticket_id,
        activity_type=activity_type,
        details=details[:512] if details else None,
        actor_id=actor_id,
        created_at_utc=_now()
    ))


def open_stop(db, asset_id: str, reason: str, actor_user_id: str | None, actor_station_code: str | None, request_id: str | None):
    stop_id = _new_id("STOP")
    now = _now()
    db.add(StopQueue(
        id=stop_id,
        site_code=settings.plant_site_code,
        asset_id=asset_id,
        reason=reason,
        is_open=True,
        opened_at_utc=now,
        closed_at_utc=None,
        resolution_text=None,
    ))

    corr_stop = f"stop_open:{stop_id}"
    timeline_append(db, asset_id, "STOP_OPEN", {"stop_id": stop_id, "reason": reason}, corr_stop)

    ticket_id = _new_id("TCK")
    sla_due = now + timedelta(minutes=60)
    db.add(Ticket(
        id=ticket_id,
        site_code=settings.plant_site_code,
        asset_id=asset_id,
        title=f"Stop: {asset_id} - {reason[:120]}",
        status="OPEN",
        priority="HIGH",
        assigned_to_user_id=None,
        source="AUTO",
        stop_id=stop_id,
        created_at_utc=now,
        sla_due_at_utc=sla_due,
        acknowledged_at_utc=None,
        resolved_at_utc=None,
        resolution_reason=None,
        close_note=None,
    ))

    log_ticket_activity(db, ticket_id, "CREATED", f"Auto-generated from Stop {stop_id}", "SYSTEM")

    corr_ticket = f"ticket_open:{ticket_id}"
    timeline_append(db, asset_id, "TICKET_OPEN", {"ticket_id": ticket_id, "stop_id": stop_id}, corr_ticket)

    enqueue_email(
        db,
        settings.email_maintenance,
        f"[{settings.plant_site_code}] STOP {asset_id} - Ticket {ticket_id}",
        f"Stop opened for asset={asset_id}\nReason={reason}\nTicket={ticket_id}\nSLA Due={sla_due.isoformat()}Z",
    )

    audit_write(db, "STOP_OPEN", "stop_queue", stop_id, {"asset_id": asset_id, "reason": reason, "ticket_id": ticket_id},
                actor_user_id, actor_station_code, request_id)

    outbox_add(db, "timeline_event", corr_stop, {"event_type":"STOP_OPEN","asset_id":asset_id,"stop_id":stop_id,"reason":reason,"occurred_at_utc":now.isoformat()+"Z"}, corr_stop)
    outbox_add(db, "ticket", ticket_id, {"ticket_id":ticket_id,"asset_id":asset_id,"stop_id":stop_id,"sla_due_at_utc":sla_due.isoformat()+"Z","status":"OPEN"}, corr_ticket)

    return {"stop_id": stop_id, "ticket_id": ticket_id, "sla_due_at_utc": sla_due.isoformat() + "Z"}


def acknowledge_ticket(db, ticket_id: str, actor_user_id: str, request_id: str | None):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise ValueError("TICKET_NOT_FOUND")
    if t.status == "CLOSED":
        raise ValueError("CANNOT_ACK_CLOSED_TICKET")
    
    if not t.acknowledged_at_utc:
        t.acknowledged_at_utc = _now()
        t.status = "ACK"
        
        # [NEW] Auto-assign to the person acknowledging if unassigned
        if not t.assigned_to_user_id:
             t.assigned_to_user_id = actor_user_id

        audit_write(db, "TICKET_ACK", "ticket", ticket_id, {}, actor_user_id, None, request_id)
        log_ticket_activity(db, ticket_id, "ACK", f"Ticket acknowledged (Assigned to {actor_user_id})", actor_user_id)
        timeline_append(db, t.asset_id, "TICKET_ACK", {"ticket_id": ticket_id, "assigned_to": actor_user_id}, f"ticket_ack:{ticket_id}")
        outbox_add(db, "ticket", ticket_id, {"ticket_id":ticket_id,"status":"ACK","assigned_to":actor_user_id,"acknowledged_at_utc":t.acknowledged_at_utc.isoformat()+"Z"}, f"ticket_ack:{ticket_id}")
    return t


def resolve_stop(db, stop_id: str, resolution_text: str, actor_user_id: str, request_id: str | None):
    sq = db.get(StopQueue, stop_id)
    if not sq:
        raise ValueError("STOP_NOT_FOUND")
    if not sq.is_open:
        return sq
    sq.is_open = False
    sq.closed_at_utc = _now()
    sq.resolution_text = resolution_text
    audit_write(db, "STOP_RESOLVE", "stop_queue", stop_id, {"resolution": resolution_text}, actor_user_id, None, request_id)
    timeline_append(db, sq.asset_id, "STOP_RESOLVE", {"stop_id": stop_id, "resolution": resolution_text}, f"stop_resolve:{stop_id}")
    outbox_add(db, "timeline_event", f"stop_resolve:{stop_id}", {"event_type":"STOP_RESOLVE","stop_id":stop_id,"asset_id":sq.asset_id,"resolution":resolution_text,"occurred_at_utc":sq.closed_at_utc.isoformat()+"Z","reason_code":sq.reason}, f"stop_resolve:{stop_id}")
    
    # [NEW] Record suggestion if it's not a master reason
    suggestion_record(db, "STOP_REASON", resolution_text, actor_user_id)
    
    return sq


def create_ticket(db, title: str, asset_id: str, priority: str, source: str = "MANUAL", stop_id: str | None = None, actor_id: str | None = None, assigned_to: str | None = None) -> Ticket:
    # [NEW] Smart Asset Creation Logic
    # 1. Case-insensitive lookup
    existing_asset = db.execute(select(Asset).where(Asset.id.ilike(asset_id))).scalars().first()
    
    final_asset_id = asset_id
    if existing_asset:
        # Use existing casing
        final_asset_id = existing_asset.id
    else:
        # Create new asset
        new_asset = Asset(
            id=asset_id,
            site_code=settings.plant_site_code,
            name=asset_id, # Default name = ID
            asset_type="MACHINE",
            is_active=True,
            created_at_utc=_now()
        )
        db.add(new_asset)
        db.flush() # Ensure ID is available if needed, though we set it explicitly
        final_asset_id = asset_id

    tid = _new_id("TCK")
    now = _now()
    # default SLA 4 hours for manual tickets, 2h for HIGH
    sla_hours = 2 if priority == "HIGH" or priority == "CRITICAL" else 4
    sla_due = now + timedelta(hours=sla_hours)
    
    t = Ticket(
        id=tid,
        site_code=settings.plant_site_code,
        # Use final_asset_id to ensure FK consistency (even if soft constraint)
        asset_id=final_asset_id, 
        title=title,
        status="OPEN",
        priority=priority,
        assigned_to_user_id=assigned_to,
        source=source,
        stop_id=stop_id,
        created_at_utc=now,
        sla_due_at_utc=sla_due,
        acknowledged_at_utc=None,
        resolved_at_utc=None,
        resolution_reason=None,
        close_note=None,
    )
    db.add(t)
    
    log_ticket_activity(db, tid, "CREATED", f"Ticket created via {source}", actor_id)
    
    corr = f"ticket_manual:{tid}"
    timeline_append(db, final_asset_id, "TICKET_CREATE", {"ticket_id": tid, "title": title}, corr)
    audit_write(db, "TICKET_CREATE", "ticket", tid, {"asset_id": final_asset_id, "title": title, "priority": priority, "assigned_to": assigned_to}, actor_id, None, None)
    outbox_add(db, "ticket", tid, {"ticket_id":tid,"asset_id":final_asset_id,"title":title,"status":"OPEN","assigned_to":assigned_to}, corr)
    return t


def close_ticket(db, ticket_id: str, close_note: str, resolution_reason: str | None = None, actor_id: str | None = None) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if not t:
        raise ValueError("TICKET_NOT_FOUND")
    if t.status == "CLOSED":
        return t
    
    t.status = "CLOSED"
    t.resolved_at_utc = _now()
    t.close_note = close_note
    t.resolution_reason = resolution_reason
    
    log_ticket_activity(db, ticket_id, "CLOSED", f"Closed. Reason: {resolution_reason or 'None'}", actor_id)

    audit_write(db, "TICKET_CLOSE", "ticket", ticket_id, {"close_note": close_note, "reason": resolution_reason}, actor_id, None, None)
    timeline_append(db, t.asset_id, "TICKET_CLOSE", {"ticket_id": ticket_id, "close_note": close_note}, f"ticket_close:{ticket_id}")
    outbox_add(db, "ticket", ticket_id, {"ticket_id":ticket_id,"status":"CLOSED","close_note":close_note}, f"ticket_close:{ticket_id}")
    return t


def assign_ticket(db, ticket_id: str, assigned_user_id: str, actor_id: str | None = None) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if not t:
        raise ValueError("TICKET_NOT_FOUND")
    
    old = t.assigned_to_user_id
    t.assigned_to_user_id = assigned_user_id
    
    log_ticket_activity(db, ticket_id, "ASSIGNED", f"Assigned to {assigned_user_id} (was {old})", actor_id)

    audit_write(db, "TICKET_ASSIGN", "ticket", ticket_id, {"assigned_to": assigned_user_id}, actor_id, None, None)
    timeline_append(db, t.asset_id, "TICKET_ASSIGN", {"ticket_id": ticket_id, "assigned_to": assigned_user_id}, f"ticket_assign:{ticket_id}")
    outbox_add(db, "ticket", ticket_id, {"ticket_id":ticket_id,"assigned_to":assigned_user_id}, f"ticket_assign:{ticket_id}")
    return t

# -----------------------------
# Asset Registry (CMMS Core)
# -----------------------------

def _validate_asset_payload(payload: dict) -> None:
    asset_code = (payload.get("asset_code") or "").strip()
    if not asset_code:
        raise ValueError("asset_code_required")
    if len(asset_code) > 64:
        raise ValueError("asset_code_too_long")
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name_required")
    category = (payload.get("category") or "").strip()
    if not category:
        raise ValueError("category_required")
    criticality = (payload.get("criticality") or "medium").strip().lower()
    if criticality not in ("low", "medium", "high", "critical"):
        raise ValueError("invalid_criticality")
    status = (payload.get("status") or "active").strip().lower()
    if status not in ("active", "inactive"):
        raise ValueError("invalid_status")
    tags = payload.get("tags") or []
    if not isinstance(tags, list):
        raise ValueError("invalid_tags")

def asset_create(db, payload: dict, actor_user_id: str | None, request_id: str | None):
    _validate_asset_payload(payload)
    site_code = settings.plant_site_code
    asset_code = payload["asset_code"].strip()

    from sqlalchemy import select
    exists = db.execute(select(Asset).where(Asset.site_code == site_code, Asset.asset_code == asset_code)).scalar_one_or_none()
    if exists:
        raise ValueError("asset_code_already_exists")

    asset_id = payload.get("id") or _new_id("AST")
    now = _now()

    a = Asset(
        id=asset_id,
        site_code=site_code,
        asset_code=asset_code,
        name=payload["name"].strip(),
        category=payload["category"].strip(),
        parent_id=payload.get("parent_id"),
        criticality=payload.get("criticality", "medium").lower(),
        tags=payload.get("tags", []),
        location_area=payload.get("location_area"),
        location_line=payload.get("location_line"),
        status=payload.get("status", "active").lower(),
        created_at_utc=now,
        updated_at_utc=now,
        created_by_user_id=actor_user_id,
    )
    db.add(a)
    db.flush()

    timeline_append(db, asset_id, "ASSET_CREATE", {"asset_code": a.asset_code, "name": a.name}, f"asset_create:{asset_id}")
    audit_write(db, "ASSET_CREATE", "asset", asset_id, {"asset_code": asset_code}, actor_user_id, None, request_id)
    outbox_add(db, "asset", asset_id, {"asset_id": asset_id, "asset_code": asset_code}, f"asset_create:{asset_id}")
    return a

def asset_get(db, asset_id: str):
    return db.get(Asset, asset_id)

def asset_tree(db):
    from sqlalchemy import select
    assets = db.execute(select(Asset).where(Asset.site_code == settings.plant_site_code, Asset.is_active == True)).scalars().all()
    by_id = {a.id: a for a in assets}
    children = {}
    for a in assets:
        pid = a.parent_id or "ROOT"
        children.setdefault(pid, []).append(a.id)

    def build(node_id: str):
        if node_id == "ROOT":
            nodes = children.get("ROOT", [])
            return [build(cid) for cid in nodes]
        a = by_id[node_id]
        return {
            "id": a.id,
            "asset_code": a.asset_code,
            "name": a.name,
            "category": a.category,
            "children": [build(cid) for cid in children.get(a.id, [])],
        }
    return build("ROOT")

# -------------------------
# Dynamic Masters
# -------------------------

def master_type_list(db, include_inactive: bool = False):
    from sqlalchemy import select
    q = select(MasterType).where(MasterType.site_code == settings.plant_site_code)
    if not include_inactive:
        q = q.where(MasterType.is_active == True)
    return db.execute(q).scalars().all()

def master_item_create(db, master_type_code: str, item_code: str, item_name: str, meta: dict | None = None, actor_id: str | None = None):
    now = _now()
    mi = MasterItem(
        site_code=settings.plant_site_code,
        master_type_code=master_type_code,
        item_code=item_code,
        item_name=item_name,
        meta_json=meta or {},
        created_at_utc=now,
        updated_at_utc=now,
    )
    db.add(mi)
    db.flush()
    audit_write(db, "MASTER_ITEM_CREATE", "master_item", str(mi.id), {"code": item_code}, actor_id, None, None)
    return mi

# -------------------------
# Self-learning Suggestions
# -------------------------

def suggestion_record(db, master_type_code: str, typed_text: str, actor_id: str | None = None, threshold: int = 5):
    import re
    from sqlalchemy import select
    norm = re.sub(r"\s+", " ", typed_text.strip().lower())
    if not norm: return None
    
    row = db.execute(select(ReasonSuggestion).where(
        ReasonSuggestion.site_code == settings.plant_site_code,
        ReasonSuggestion.master_type_code == master_type_code,
        ReasonSuggestion.normalized_key == norm
    )).scalar_one_or_none()

    now = _now()
    if not row:
        row = ReasonSuggestion(
            site_code=settings.plant_site_code,
            master_type_code=master_type_code,
            suggested_name=typed_text,
            normalized_key=norm,
            count=1,
            status="pending",
            threshold=threshold,
            created_at_utc=now,
            updated_at_utc=now,
            created_by_user_id=actor_id
        )
        db.add(row)
    else:
        row.count += 1
        row.updated_at_utc = now
        if row.count >= row.threshold and row.status == "pending":
            row.status = "auto_promoted"
            enqueue_email(db, settings.email_maintenance, f"Suggestion Auto-Promoted: {norm}", f"The reason '{typed_text}' has been used {row.count} times.")
    
    db.flush()
    return row

def suggestion_approve(db, suggestion_id: int, item_code: str, actor_id: str):
    s = db.get(ReasonSuggestion, suggestion_id)
    if not s or s.status in ("approved", "merged"): return s
    
    mi = master_item_create(db, s.master_type_code, item_code, s.suggested_name, {"from_suggestion": s.id}, actor_id)
    s.status = "approved"
    s.approved_master_item_id = mi.id
    s.reviewed_by_user_id = actor_id
    s.reviewed_at_utc = _now()
    return s

# -----------------------------
# Reporting v1 (manual trigger)
# -----------------------------

def _parse_iso_date(s: str) -> datetime:
    s = (s or "").strip()
    if not s:
        raise ValueError("date is required")
    # Accept YYYY-MM-DD or ISO datetime
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return datetime.fromisoformat(s + "T00:00:00")
    return datetime.fromisoformat(s)

def report_request_create_and_generate_csv(
    db,
    report_type: str,
    date_from: str,
    date_to: str,
    filters: dict,
    actor_user_id: str,
    actor_station_code: str | None,
    request_id: str | None,
) -> ReportRequest:
    import json
    import re
    import os
    import csv
    from apps.plant_backend.models import StopQueue # Use StopQueue from models.py

    dt_from = _parse_iso_date(date_from)
    dt_to = _parse_iso_date(date_to)
    if dt_to < dt_from:
        raise ValueError("date_to must be >= date_from")

    rr = ReportRequest(
        site_code=settings.plant_site_code,
        report_type=report_type,
        date_from=dt_from,
        date_to=dt_to,
        filters_json=json.dumps(filters or {}, ensure_ascii=False),
        requested_by_user_id=actor_user_id,
        status="requested",
        generated_file_path=None,
        error_message=None,
        created_at_utc=_now(),
        updated_at_utc=_now(),
    )
    db.add(rr)
    db.flush()

    audit_write(db, "REPORT_REQUEST", "report_request", str(rr.id), {"type": report_type}, actor_user_id, actor_station_code, request_id)

    # Generate synchronously
    try:
        vault_root = settings.report_vault_root
        os.makedirs(vault_root, exist_ok=True)
        safe_type = re.sub(r"[^a-zA-Z0-9_\\-]", "_", report_type)[:64]
        filename = f"report_{safe_type}_{rr.site_code}_{rr.id}.csv"
        file_path = os.path.join(vault_root, filename)

        if report_type == "downtime_by_asset":
            # Implementation for downtime_by_asset
            from sqlalchemy import select
            stops = db.execute(select(StopQueue).where(
                StopQueue.site_code == rr.site_code,
                StopQueue.opened_at_utc >= dt_from,
                StopQueue.opened_at_utc <= dt_to
            )).scalars().all()
            
            agg = {}
            for s in stops:
                # Calculate duration in seconds
                end = s.closed_at_utc or dt_to
                dur = (end - s.opened_at_utc).total_seconds()
                agg[s.asset_id] = agg.get(s.asset_id, 0.0) + max(0, dur)
            
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["site_code", "date_from", "date_to", "asset_id", "downtime_seconds"])
                for asset_id, total in sorted(agg.items(), key=lambda x: x[1], reverse=True):
                    w.writerow([rr.site_code, dt_from.isoformat(), dt_to.isoformat(), asset_id, int(total)])
        else:
            # Default summary
            from sqlalchemy import select
            stops = db.execute(select(StopQueue).where(
                StopQueue.site_code == rr.site_code,
                StopQueue.opened_at_utc >= dt_from,
                StopQueue.opened_at_utc <= dt_to
            )).scalars().all()
            
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["section", "site_code", "date_from", "date_to", "field", "value"])
                w.writerow(["summary", rr.site_code, dt_from.isoformat(), dt_to.isoformat(), "stops_count", len(stops)])

        rr.status = "generated"
        rr.generated_file_path = filename
        rr.updated_at_utc = _now()
        audit_write(db, "REPORT_GENERATED", "report_request", str(rr.id), {"path": filename}, actor_user_id, actor_station_code, request_id)
    except Exception as e:
        rr.status = "failed"
        rr.error_message = str(e)
        rr.updated_at_utc = _now()
        audit_write(db, "REPORT_FAILED", "report_request", str(rr.id), {"error": str(e)}, actor_user_id, actor_station_code, request_id)
    
    return rr
