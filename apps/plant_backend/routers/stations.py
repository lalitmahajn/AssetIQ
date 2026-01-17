from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.plant_backend.security_deps import require_roles
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("/config")
def config():
    # Shared PC mandatory enforcement is handled on UI; backend provides policy hints.
    return {
        "auto_lock_seconds": 45,
        "stop_queue_visible": True,
        "station_identity_is_not_user": True,
    }


class StationRegisterIn(BaseModel):
    station_code: str = Field(min_length=2, max_length=32)


@router.post("/register")
def register(body: StationRegisterIn, claims=Depends(require_roles("admin"))):
    db = PlantSessionLocal()
    try:
        from datetime import datetime

        from apps.plant_backend.models import Station
        from common_core.hash_utils import generate_salt, hash_secret

        stmt = select(Station).where(Station.station_code == body.station_code)
        existing = db.execute(stmt).scalar_one_or_none()

        # Determine secret
        raw_secret = f"s-{body.station_code}-{generate_salt(6)}"
        salt = generate_salt()

        if existing:
            existing.secret_hash = hash_secret(raw_secret, salt)
            existing.token_salt = salt
            existing.is_active = True
        else:
            new_st = Station(
                station_code=body.station_code,
                description=f"Station {body.station_code}",
                secret_hash=hash_secret(raw_secret, salt),
                token_salt=salt,
                is_active=True,
                created_at_utc=datetime.utcnow(),
            )
            db.add(new_st)

        db.commit()
        return {"ok": True, "station_code": body.station_code, "secret": raw_secret}
    finally:
        db.close()


@router.post("/rotate-secret")
def rotate(body: StationRegisterIn, claims=Depends(require_roles("admin"))):
    # Same logic as register for now, effectively resets secret
    return register(body, claims)
