from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from typing import List, Optional

from common_core.db import PlantSessionLocal
from common_core.passwords import hash_pin
from common_core.config import settings
from apps.plant_backend.models import User, ReasonSuggestion, AuditLog, Asset
from apps.plant_backend.security_deps import require_roles

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
    has_pin: bool

class CreateUserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    pin: str = Field(min_length=6, max_length=32)
    roles: str = "maintenance"

class AuditLogItem(BaseModel):
    id: int
    actor_user_id: Optional[str]
    action: str
    entity_type: str
    entity_id: str
    created_at_utc: str 
    details: str

class AssetItem(BaseModel):
    id: str
    site_code: str
    name: str
    parent_id: Optional[str]
    asset_type: str
    description: Optional[str]
    is_active: bool

class AssetCreateIn(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parent_id: Optional[str] = None
    asset_type: str = "MACHINE"
    description: Optional[str] = None

class AssetUpdateIn(BaseModel):
    id: str
    name: Optional[str] = None
    parent_id: Optional[str] = None
    asset_type: Optional[str] = None
    description: Optional[str] = None

class UserUpdateIn(BaseModel):
    username: str
    pin: Optional[str] = None
    roles: Optional[str] = None

class ReasonMergeIn(BaseModel):
    source_id: int
    target_id: int

@router.get("/reasons/list", response_model=List[ReasonItem])
def list_reasons(q: Optional[str] = None, limit: int = 50, claims=Depends(require_roles("admin", "supervisor"))):
    db = PlantSessionLocal()
    try:
        query = select(ReasonSuggestion).where(ReasonSuggestion.is_active == True)
        if q:
            query = query.where(ReasonSuggestion.suggested_name.ilike(f"%{q}%"))
        
        reasons = db.execute(query.limit(limit)).scalars().all()
        
        return [
            ReasonItem(
                id=r.id, 
                text=r.suggested_name, 
                category="General", # master_type_code default? Model says 'master_type_code' but we don't have category col anymore in provided dump?
                usage_count=r.count, 
                is_active=r.is_active
            ) for r in reasons
        ]
    finally:
        db.close()

@router.post("/reasons/create")
def create_reason(body: ReasonCreateIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        # Check dupe?
        existing = db.execute(select(ReasonSuggestion).where(ReasonSuggestion.suggested_name == body.text)).scalar_one_or_none()
        if existing and existing.is_active:
            raise HTTPException(status_code=409, detail="REASON_EXISTS")
        
        from common_core.config import settings
        new_r = ReasonSuggestion(
            site_code="P01", # hardcoded as per prev file or fetch env
            suggested_name=body.text,
            normalized_key=body.text.upper(), # simplistic normalization
            # category removed? Model doesn't have it.
        )
        db.add(new_r)
        db.commit()
        return {"ok": True, "id": new_r.id}
    finally:
        db.close()

@router.post("/reasons/delete")
def delete_reason(id: int, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        r = db.execute(select(ReasonSuggestion).where(ReasonSuggestion.id == id)).scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="NOT_FOUND")
        r.is_active = False # Soft delete
        db.commit()
        return {"ok": True}
    finally:
        db.close()

# 2. User Management
@router.get("/users/list", response_model=List[UserItem])
def list_users(claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        users = db.execute(select(User)).scalars().all()
        return [
            {"id": u.id, "roles": u.roles, "has_pin": True}
            for u in users
        ]
    finally:
        db.close()

@router.post("/users/create")
def create_user(body: CreateUserIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        existing = db.execute(select(User).where(User.id == body.username)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="USER_EXISTS")
        
        new_user = User(
            id=body.username,
            pin_hash=hash_pin(body.pin),
            roles=body.roles
        )
        db.add(new_user)
        db.commit()
        return {"ok": True, "username": body.username}
    finally:
        db.close()

# 3. Audit Logs
@router.get("/audit/list", response_model=List[AuditLogItem])
def list_audit(limit: int = 50, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        # Fetch latest logs
        logs = db.execute(
            select(AuditLog).order_by(desc(AuditLog.id)).limit(limit)
        ).scalars().all()
        
        return [
            AuditLogItem(
                id=l.id,
                actor_user_id=l.actor_user_id,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                created_at_utc=l.created_at_utc.isoformat(),
                details=str(l.details_json)
            ) for l in logs
        ]
    finally:
        db.close()

# 4. Asset Management
@router.get("/assets/list", response_model=List[AssetItem])
def list_assets(q: Optional[str] = None, limit: int = 50, claims=Depends(require_roles("admin", "supervisor", "operator"))):
    db = PlantSessionLocal()
    try:
        query = select(Asset).where(Asset.is_active == True)
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
                asset_type=a.asset_type,
                description=a.description,
                is_active=a.is_active
            ) for a in assets
        ]
    finally:
        db.close()

@router.post("/assets/create")
def create_asset(body: AssetCreateIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        existing = db.execute(select(Asset).where(Asset.id == body.id)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="ASSET_EXISTS")
        
        new_asset = Asset(
            id=body.id,
            site_code=settings.plant_site_code,
            name=body.name,
            parent_id=body.parent_id,
            asset_type=body.asset_type,
            description=body.description,
            created_at_utc=datetime.utcnow()
        )
        db.add(new_asset)
        db.commit()
        return {"ok": True, "id": new_asset.id}
    finally:
        db.close()

@router.post("/assets/update")
def update_asset(body: AssetUpdateIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        asset = db.execute(select(Asset).where(Asset.id == body.id)).scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="NOT_FOUND")
        
        if body.name is not None: asset.name = body.name
        if body.parent_id is not None: asset.parent_id = body.parent_id
        if body.asset_type is not None: asset.asset_type = body.asset_type
        if body.description is not None: asset.description = body.description
        
        db.commit()
        return {"ok": True}
    finally:
        db.close()

# 5. Advanced User Management
@router.post("/users/update")
def update_user(body: UserUpdateIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        user = db.execute(select(User).where(User.id == body.username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="NOT_FOUND")
        
        if body.pin:
            user.pin_hash = hash_pin(body.pin)
        if body.roles:
            user.roles = body.roles
            
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@router.post("/users/delete")
def delete_user(username: str, claims=Depends(require_roles("admin"))):
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
def merge_reasons(body: ReasonMergeIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        source = db.execute(select(ReasonSuggestion).where(ReasonSuggestion.id == body.source_id)).scalar_one_or_none()
        target = db.execute(select(ReasonSuggestion).where(ReasonSuggestion.id == body.target_id)).scalar_one_or_none()
        
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
@router.get("/config")
def get_config(claims=Depends(require_roles("admin"))):
    # Fetch from environment
    import os
    site_code = os.getenv("PLANT_SITE_CODE", "Unknown")
    
    return {
        "plantName": f"Plant {site_code}", # Simple formatting
        "siteCode": site_code,
        "enableWhatsApp": False, # Placeholder
        "stopQueueVisible": True,
        "autoLogoutMinutes": 30
    }
