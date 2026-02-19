from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.plant_backend.deps import require_perm
from apps.plant_backend.services import asset_create, asset_tree
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetCreateIn(BaseModel):
    asset_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    parent_id: str | None = None
    is_critical: bool = False
    location_area: str | None = None
    sub_location_area: str | None = None


@router.post("/create")
def create(body: AssetCreateIn, user: Annotated[Any, Depends(require_perm("asset.manage"))] = None):
    db = PlantSessionLocal()
    try:
        a = asset_create(db, body.dict(), user["sub"], None)
        db.commit()
        return {"ok": True, "id": a.id}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        db.close()


@router.get("/tree")
def tree(user: Annotated[Any, Depends(require_perm("asset.view"))] = None):
    db = PlantSessionLocal()
    try:
        return asset_tree(db)
    finally:
        db.close()


@router.get("/list")
def list_assets(
    q: str | None = None,
    user: Annotated[Any, Depends(require_perm("asset.view"))] = None,
):
    db = PlantSessionLocal()
    try:
        from sqlalchemy import or_

        from apps.plant_backend.models import Asset

        stmt = select(Asset).where(Asset.is_active.is_(True))
        if q:
            stmt = stmt.where(or_(Asset.name.ilike(f"%{q}%"), Asset.asset_code.ilike(f"%{q}%")))

        rows = db.execute(stmt.order_by(Asset.asset_code)).scalars().all()
        return [
            {
                "id": r.id,
                "asset_code": r.asset_code,
                "name": r.name,
                "category": r.category,
                "is_critical": r.is_critical,
            }
            for r in rows
        ]
    finally:
        db.close()
