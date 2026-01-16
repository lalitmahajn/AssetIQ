from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from common_core.db import PlantSessionLocal
from apps.plant_backend.deps import require_perm
from apps.plant_backend.services import asset_create, asset_get, asset_tree
from sqlalchemy import select
from apps.plant_backend.models import Asset

router = APIRouter(prefix="/assets", tags=["assets"])

class AssetCreateIn(BaseModel):
    asset_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    parent_id: Optional[str] = None
    criticality: str = "medium"
    location_area: Optional[str] = None
    location_line: Optional[str] = None

@router.post("/create")
def create(body: AssetCreateIn, user=Depends(require_perm("asset.manage"))):
    db = PlantSessionLocal()
    try:
        a = asset_create(db, body.dict(), user["sub"], None)
        db.commit()
        return {"ok": True, "id": a.id}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.get("/tree")
def tree(user=Depends(require_perm("asset.view"))):
    db = PlantSessionLocal()
    try:
        return asset_tree(db)
    finally:
        db.close()

@router.get("/list")
def list_assets(user=Depends(require_perm("asset.view"))):
    db = PlantSessionLocal()
    try:
        from apps.plant_backend.models import Asset
        rows = db.execute(select(Asset).where(Asset.is_active == True).order_by(Asset.asset_code)).scalars().all()
        return [{"id":r.id, "asset_code":r.asset_code, "name":r.name, "category":r.category} for r in rows]
    finally:
        db.close()
