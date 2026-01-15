from __future__ import annotations

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from common_core.db import PlantSessionLocal
from common_core.passwords import hash_pin
from apps.plant_backend.models import User

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


class BootstrapAdminIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=8, max_length=32)
    roles: str = Field(default="admin,supervisor,maintenance", max_length=256)


@router.post("/create-admin")
def create_admin(body: BootstrapAdminIn, request: Request):
    token = request.headers.get("X-Bootstrap-Token") or ""
    expected = os.environ.get("BOOTSTRAP_TOKEN") or ""
    if not expected or token != expected:
        raise HTTPException(status_code=403, detail="BOOTSTRAP_FORBIDDEN")

    db = PlantSessionLocal()
    try:
        any_user = db.execute(select(User).limit(1)).scalar_one_or_none()
        if any_user:
            raise HTTPException(status_code=409, detail="BOOTSTRAP_ALREADY_DONE")
        db.add(User(id=body.username, pin_hash=hash_pin(body.pin), roles=body.roles))
        db.commit()
        return {"ok": True, "created_at_utc": datetime.utcnow().isoformat() + "Z"}
    finally:
        db.close()
