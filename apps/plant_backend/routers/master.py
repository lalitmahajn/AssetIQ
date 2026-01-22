from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from apps.plant_backend.models import Asset, AuditLog, ReasonSuggestion, User
from apps.plant_backend.security_deps import require_roles
from common_core.config import settings
from common_core.db import PlantSessionLocal
from common_core.passwords import hash_pin

router = APIRouter(prefix="/master", tags=["master"])


# ---- Models ----
class ReasonItem(BaseModel):
    id: int
    text: str
    category: str
    usage_count: int
    is_active: bool


class ReasonCreateIn(BaseModel):
    text: str = Field(min_length=1)
    category: str = "Other"


class ReasonUpdateIn(BaseModel):
    id: int
    text: str
    category: str


class UserItem(BaseModel):
    id: str
    roles: str
    full_name: str | None
    has_pin: bool


class CreateUserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str | None = None
    pin: str = Field(min_length=6, max_length=32)
    roles: str = "maintenance"


class AuditLogItem(BaseModel):
    id: int
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    created_at_utc: str
    details: str


class AssetItem(BaseModel):
    id: str
    site_code: str
    name: str
    parent_id: str | None
    asset_type: str
    description: str | None
    is_active: bool
    is_critical: bool


class AssetCreateIn(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=256)
    parent_id: str | None = None
    asset_type: str = "MACHINE"
    description: str | None = None
    is_critical: bool = False


class AssetUpdateIn(BaseModel):
    id: str
    name: str | None = None
    parent_id: str | None = None
    asset_type: str | None = None
    description: str | None = None
    is_critical: bool | None = None


class UserUpdateIn(BaseModel):
    username: str
    full_name: str | None = None
    pin: str | None = None
    roles: str | None = None


class ReasonMergeIn(BaseModel):
    source_id: int
    target_id: int


@router.get("/reasons/list", response_model=list[ReasonItem])
def list_reasons(
    q: str | None = None,
    limit: int = 50,
    claims: Annotated[Any, Depends(require_roles("admin", "supervisor"))] = None,
):
    db = PlantSessionLocal()
    try:
        query = select(ReasonSuggestion).where(ReasonSuggestion.is_active.is_(True))
        if q:
            query = query.where(ReasonSuggestion.suggested_name.ilike(f"%{q}%"))

        reasons = db.execute(query.limit(limit)).scalars().all()

        return [
            ReasonItem(
                id=r.id,
                text=r.suggested_name,
                category="General",  # master_type_code default? Model says 'master_type_code' but we don't have category col anymore in provided dump?
                usage_count=r.count,
                is_active=r.is_active,
            )
            for r in reasons
        ]
    finally:
        db.close()


@router.post("/reasons/create")
def create_reason(
    body: ReasonCreateIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None
):
    db = PlantSessionLocal()
    try:
        # Check dupe?
        existing = db.execute(
            select(ReasonSuggestion).where(ReasonSuggestion.suggested_name == body.text)
        ).scalar_one_or_none()
        if existing and existing.is_active:
            raise HTTPException(status_code=409, detail="REASON_EXISTS")

        from common_core.config import settings

        new_r = ReasonSuggestion(
            site_code=settings.plant_site_code,  # Use settings instead of hardcoded
            suggested_name=body.text,
            normalized_key=body.text.upper(),  # simplistic normalization
            # category removed? Model doesn't have it.
        )
        db.add(new_r)
        db.commit()
        return {"ok": True, "id": new_r.id}
    finally:
        db.close()


@router.post("/reasons/delete")
def delete_reason(id: int, claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        r = db.execute(
            select(ReasonSuggestion).where(ReasonSuggestion.id == id)
        ).scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="NOT_FOUND")
        r.is_active = False  # Soft delete
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# 2. User Management
@router.get("/users/list", response_model=list[UserItem])
def list_users(claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        users = db.execute(select(User)).scalars().all()
        return [
            {"id": u.id, "roles": u.roles, "full_name": u.full_name, "has_pin": True} for u in users
        ]
    finally:
        db.close()


@router.post("/users/create")
def create_user(body: CreateUserIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        existing = db.execute(select(User).where(User.id == body.username)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="USER_EXISTS")

        new_user = User(
            id=body.username,
            pin_hash=hash_pin(body.pin),
            roles=body.roles,
            full_name=body.full_name,
        )
        db.add(new_user)
        db.commit()
        return {"ok": True, "username": body.username}
    finally:
        db.close()


# 3. Audit Logs
@router.get("/audit/list")
def list_audit(
    limit: int = 50,
    offset: int = 0,
    claims: Annotated[Any, Depends(require_roles("admin"))] = None,
):
    db = PlantSessionLocal()
    try:
        # Total count for pagination
        from sqlalchemy import func

        total = db.execute(select(func.count()).select_from(AuditLog)).scalar()

        # Fetch latest logs with offset and limit
        logs = (
            db.execute(select(AuditLog).order_by(desc(AuditLog.id)).offset(offset).limit(limit))
            .scalars()
            .all()
        )

        items = [
            {
                "id": log_item.id,
                "actor_user_id": log_item.actor_user_id,
                "action": log_item.action,
                "entity_type": log_item.entity_type,
                "entity_id": log_item.entity_id,
                "created_at_utc": log_item.created_at_utc.isoformat(),
                "details": log_item.details_json,
            }
            for log_item in logs
        ]
        return {"items": items, "total": total}
    finally:
        db.close()


# 4. Asset Management
@router.get("/assets/list", response_model=list[AssetItem])
def list_assets(
    q: str | None = None,
    limit: int = 50,
    claims: Annotated[Any, Depends(require_roles("admin", "supervisor", "operator"))] = None,
):
    db = PlantSessionLocal()
    try:
        query = select(Asset).where(Asset.is_active.is_(True))
        if q:
            # Simple case-insensitive match on ID or Name
            from sqlalchemy import or_

            query = query.where(or_(Asset.id.ilike(f"%{q}%"), Asset.name.ilike(f"%{q}%")))

        # Apply limit
        assets = db.execute(query.limit(limit)).scalars().all()

        return [
            AssetItem(
                id=a.id,
                site_code=a.site_code,
                name=a.name,
                parent_id=a.parent_id,
                asset_type=a.category,  # Map category back to asset_type for UI compatibility if needed, though AssetItem says asset_type
                description=a.description,
                is_active=a.is_active,
                is_critical=a.is_critical,
            )
            for a in assets
        ]
    finally:
        db.close()


@router.post("/assets/create")
def create_asset(
    body: AssetCreateIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None
):
    db = PlantSessionLocal()
    try:
        existing = db.execute(select(Asset).where(Asset.id == body.id)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="ASSET_EXISTS")

        new_asset = Asset(
            id=body.id,
            site_code=settings.plant_site_code,
            asset_code=body.id,  # Using ID as asset_code for simplicity
            name=body.name,
            category=body.asset_type,  # Mapping UI's asset_type to database category
            parent_id=body.parent_id,
            description=body.description,
            created_at_utc=datetime.utcnow(),
            is_active=True,
            is_critical=body.is_critical,
        )
        db.add(new_asset)
        db.commit()
        return {"ok": True, "id": new_asset.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()


@router.post("/assets/update")
def update_asset(
    body: AssetUpdateIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None
):
    db = PlantSessionLocal()
    try:
        asset = db.execute(select(Asset).where(Asset.id == body.id)).scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="NOT_FOUND")

        if body.name is not None:
            asset.name = body.name
        if body.parent_id is not None:
            asset.parent_id = body.parent_id
        if body.asset_type is not None:
            asset.asset_type = body.asset_type
        if body.description is not None:
            asset.description = body.description
        if body.is_critical is not None:
            asset.is_critical = body.is_critical

        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/assets/delete")
def delete_asset(asset_id: str, claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    """Soft deletes an asset by setting is_active to False."""
    db = PlantSessionLocal()
    try:
        asset = db.execute(select(Asset).where(Asset.id == asset_id)).scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="NOT_FOUND")

        asset.is_active = False
        asset.updated_at_utc = datetime.utcnow()
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# 5. Advanced User Management
@router.post("/users/update")
def update_user(body: UserUpdateIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        user = db.execute(select(User).where(User.id == body.username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="NOT_FOUND")

        if body.pin:
            user.pin_hash = hash_pin(body.pin)
        if body.roles:
            user.roles = body.roles
        if body.full_name is not None:
            user.full_name = body.full_name

        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/users/delete")
def delete_user(username: str, claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        user = db.execute(select(User).where(User.id == username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="NOT_FOUND")

        db.delete(user)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# 6. Reason Merge
@router.post("/reasons/merge")
def merge_reasons(
    body: ReasonMergeIn, claims: Annotated[Any, Depends(require_roles("admin"))] = None
):
    db = PlantSessionLocal()
    try:
        source = db.execute(
            select(ReasonSuggestion).where(ReasonSuggestion.id == body.source_id)
        ).scalar_one_or_none()
        target = db.execute(
            select(ReasonSuggestion).where(ReasonSuggestion.id == body.target_id)
        ).scalar_one_or_none()

        if not source or not target:
            raise HTTPException(status_code=404, detail="NOT_FOUND")

        # "Merge" logic: Soft delete source.
        # Ideally, we would update historical stops, but for now we just disable the bad reason.
        source.is_active = False

        # Log this action?
        # db.add(AuditLog(...))

        db.commit()
        return {"ok": True}
    finally:
        db.close()


# 7. Configuration
from apps.plant_backend.models import SystemConfig


@router.get("/config")
def get_config(claims: Annotated[Any, Depends(require_roles("admin"))] = None):
    db = PlantSessionLocal()
    try:
        # Default config
        import os

        site_code = os.getenv("PLANT_SITE_CODE", "Unknown")
        config = {
            "plantName": f"Plant {site_code}",
            "siteCode": site_code,
            "stopQueueVisible": True,
            "autoLogoutMinutes": 30,
            "whatsappEnabled": False,
            "whatsappTargetPhone": "",
            "whatsappMessageTemplate": "🚀 AssetIQ Ticket Created\nID: {id}\nAsset: {asset_id}\nTitle: {title}\nPriority: {priority}",
            "whatsappCloseMessageTemplate": "✅ Ticket Closed\nID: {id}\nNote: {close_note}",
        }

        # Override with DB values
        rows = db.execute(select(SystemConfig)).scalars().all()
        for row in rows:
            config[row.config_key] = row.config_value

        return config
    finally:
        db.close()


@router.post("/config")
def set_config(
    payload: dict,
    claims: Annotated[Any, Depends(require_roles("admin"))] = None,
):
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        updated_state = {}

        # Log payload for debugging
        import logging

        logging.getLogger("assetiq").info(f"SET_CONFIG payload: {payload}")

        for k, v in payload.items():
            # Only allow specific keys
            if k not in [
                "stopQueueVisible",
                "autoLogoutMinutes",
                "whatsappEnabled",
                "whatsappTargetPhone",
                "whatsappMessageTemplate",
                "whatsappCloseMessageTemplate",
                "whatsappWarningMessageTemplate",
                "whatsappBreachMessageTemplate",
                "whatsappHeartbeat",
                "whatsappLogoutRequest",
                "whatsappSlaWarningThresholdMinutes",
            ]:
                continue

            # Validation
            if k == "autoLogoutMinutes":
                try:
                    val = int(v)
                    if val < 1:
                        continue  # Or raise error
                except:
                    continue

            row = db.get(SystemConfig, k)
            if row:
                row.config_value = v
                row.updated_at_utc = now
            else:
                db.add(SystemConfig(config_key=k, config_value=v, updated_at_utc=now))

            # Add to response for UI update
            updated_state[k] = v

        db.commit()
        return {"status": "ok", "updated": updated_state}
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger("assetiq").error(f"SET_CONFIG FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/simulate/sla_warning")
def simulate_sla_warning(
    claims: Annotated[Any, Depends(require_roles("admin"))] = None,
):
    """Sets the latest open ticket's SLA to be approaching (threshold - 5 mins)"""
    from sqlalchemy import desc, select

    from apps.plant_backend.models import SystemConfig, Ticket

    db = PlantSessionLocal()
    try:
        # Get threshold
        threshold = 60
        row = db.get(SystemConfig, "whatsappSlaWarningThresholdMinutes")
        if row:
            try:
                threshold = int(row.config_value)
            except:
                pass

        # Find latest open ticket
        t = db.execute(
            select(Ticket)
            .where(Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"]))
            .order_by(desc(Ticket.created_at_utc))
            .limit(1)
        ).scalar()

        if not t:
            return {"status": "error", "message": "No open tickets found for simulation."}

        # Set SLA to be threshold - 5 minutes from now
        # This ensures it hits the warning logic
        new_sla = datetime.utcnow() + timedelta(minutes=threshold - 5)
        t.sla_due_at_utc = new_sla
        t.sla_warning_sent = False
        db.commit()

        return {
            "status": "ok",
            "message": f"Ticket {t.id} SLA updated to {new_sla} (approaching warning).",
            "ticket_id": t.id,
        }
    finally:
        db.close()


@router.post("/simulate/sla_breach")
def simulate_sla_breach(
    claims: Annotated[Any, Depends(require_roles("admin"))] = None,
):
    """Sets the latest open ticket's SLA to be in the past"""
    from sqlalchemy import desc, select

    from apps.plant_backend.models import Ticket

    db = PlantSessionLocal()
    try:
        # Find latest open ticket
        t = db.execute(
            select(Ticket)
            .where(Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"]))
            .order_by(desc(Ticket.created_at_utc))
            .limit(1)
        ).scalar()

        if not t:
            return {"status": "error", "message": "No open tickets found for simulation."}

        # Set SLA to 15 minutes ago
        new_sla = datetime.utcnow() - timedelta(minutes=15)
        t.sla_due_at_utc = new_sla
        db.commit()

        return {
            "status": "ok",
            "message": f"Ticket {t.id} SLA updated to {new_sla} (breached).",
            "ticket_id": t.id,
        }
    finally:
        db.close()


@router.post("/simulate/stop")
def simulate_stop(
    claims: Annotated[Any, Depends(require_roles("admin"))] = None,
):
    """Triggers a simulated machine stop for the first asset found"""
    from sqlalchemy import select

    from apps.plant_backend.models import Asset
    from apps.plant_backend.runtime import sse_bus
    from apps.plant_backend.services import open_stop

    db = PlantSessionLocal()
    try:
        # Find an asset to stop
        asset = db.execute(select(Asset).limit(1)).scalar()
        if not asset:
            return {"status": "error", "message": "No assets found to simulate a stop on."}

        res = open_stop(
            db,
            asset.id,
            "SIMULATED_TEST_STOP",
            claims["sub"] if claims else "admin",
            "ADMIN_UI",
            None,
        )

        db.commit()

        # Notify UI via SSE
        sse_bus.publish(
            {
                "type": "STOP_OPEN",
                "stop_id": res["stop_id"],
                "asset_id": asset.id,
                "reason": "SIMULATED_TEST_STOP",
            }
        )

        return {
            "status": "ok",
            "message": f"Stop {res['stop_id']} triggered for asset {asset.id}.",
            "stop_id": res["stop_id"],
            "ticket_id": res["ticket_id"],
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
