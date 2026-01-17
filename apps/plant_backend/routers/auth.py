from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.plant_backend.models import User
from apps.plant_backend.security_rate_limit import login_limiter
from common_core.db import PlantSessionLocal
from common_core.passwords import verify_pin
from common_core.security import issue_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=4, max_length=32)


@router.post("/login")
def login(body: LoginIn, request: Request):
    if request.headers.get("X-Station-Mode") == "1":
        raise HTTPException(status_code=403, detail="STATION_MODE_FORBIDDEN")

    ip = request.client.host if request.client else "unknown"
    if not login_limiter.allow(ip, body.username):
        raise HTTPException(status_code=429, detail="RATE_LIMITED")

    db = PlantSessionLocal()
    try:
        u = db.execute(select(User).where(User.id == body.username)).scalar_one_or_none()
        if not u or not verify_pin(body.pin, u.pin_hash):
            raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")

        roles = [r.strip() for r in (u.roles or "").split(",") if r.strip()]
        return {"token": issue_jwt(sub=u.id, roles=roles), "roles": roles}
    finally:
        db.close()
