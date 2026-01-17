from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from apps.plant_backend.deps import require_perm
from apps.plant_backend.models import MasterItem, MasterType
from apps.plant_backend.services import master_item_create
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/masters-dynamic", tags=["masters-dynamic"])


@router.get("/types")
def list_types(user=Depends(require_perm("master.view"))):
    db = PlantSessionLocal()
    try:
        rows = db.execute(select(MasterType).where(MasterType.is_active.is_(True))).scalars().all()
        return [{"type_code": r.type_code, "name": r.name} for r in rows]
    finally:
        db.close()


@router.get("/items")
def list_items(type_code: str, user=Depends(require_perm("master.view"))):
    db = PlantSessionLocal()
    try:
        rows = (
            db.execute(
                select(MasterItem)
                .where(MasterItem.master_type_code == type_code, MasterItem.is_active.is_(True))
                .order_by(MasterItem.item_code)
            )
            .scalars()
            .all()
        )
        return [{"id": r.id, "item_code": r.item_code, "item_name": r.item_name} for r in rows]
    finally:
        db.close()


@router.post("/items/create")
def create_item(body: dict, user=Depends(require_perm("master.manage"))):
    type_code = body.get("type_code")
    item_code = body.get("item_code")
    item_name = body.get("item_name")
    if not type_code or not item_code or not item_name:
        raise HTTPException(status_code=400, detail="Missing fields")
    db = PlantSessionLocal()
    try:
        mi = master_item_create(db, type_code, item_code, item_name, None, user["sub"])
        db.commit()
        return {"ok": True, "id": mi.id}
    finally:
        db.close()
