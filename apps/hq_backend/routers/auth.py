from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from common_core.db import HQSessionLocal
from common_core.passwords import verify_pin
from common_core.security import issue_jwt, verify_jwt
from apps.hq_backend.models import HQUser

router = APIRouter(prefix="/hq/auth", tags=["hq-auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=4, max_length=32)


@router.post("/login")
def login(body: LoginIn, response: Response):
    db = HQSessionLocal()
    try:
        username = body.username.strip()
        pin = body.pin.strip()
        u = db.execute(select(HQUser).where(HQUser.username == username)).scalar_one_or_none()
        if not u or not verify_pin(pin, u.pin_hash):
            raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")

        roles = [r.strip() for r in (u.roles or "").split(",") if r.strip()]
        token = issue_jwt(sub=u.username, roles=roles)

        # Set cookie for the UI
        response.set_cookie(
            key="hq_access_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=8 * 60 * 60,  # 8 hours
        )

        return {"token": token, "roles": roles}
    finally:
        db.close()


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("hq_access_token")
    return {"status": "ok"}


class CreateUserIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=6, max_length=32)
    roles: str = "user"


def _get_current_admin(request: Request):
    token = request.cookies.get("hq_access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")

    try:
        payload = verify_jwt(token)
        roles = payload.get("roles", [])
        if "admin" not in roles:
            raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")


@router.post("/create-user")
def create_user(body: CreateUserIn, admin: dict = Depends(_get_current_admin)):
    db = HQSessionLocal()
    try:
        username = body.username.strip()
        pin = body.pin.strip()

        existing = db.execute(
            select(HQUser).where(HQUser.username == username)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="USER_EXISTS")

        from common_core.passwords import hash_pin

        user = HQUser(
            username=username,
            pin_hash=hash_pin(pin),
            roles=body.roles,
            created_at_utc=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        return {"status": "created", "username": user.username}
    finally:
        db.close()


@router.get("/users")
def list_users(admin: dict = Depends(_get_current_admin)):
    """List all registered HQ users"""
    db = HQSessionLocal()
    try:
        users = db.execute(select(HQUser).order_by(HQUser.created_at_utc.desc())).scalars().all()
        return {
            "items": [
                {
                    "username": u.username,
                    "roles": u.roles,
                    "created_at_utc": u.created_at_utc.isoformat() if u.created_at_utc else None,
                }
                for u in users
            ]
        }
    finally:
        db.close()


@router.delete("/users/{username}")
def delete_user(username: str, admin: dict = Depends(_get_current_admin)):
    """Delete a user by username"""
    if username == admin.get("sub"):
        raise HTTPException(status_code=400, detail="CANNOT_DELETE_SELF")

    db = HQSessionLocal()
    try:
        u = db.execute(select(HQUser).where(HQUser.username == username)).scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

        db.delete(u)
        db.commit()
        return {"status": "deleted", "username": username}
    finally:
        db.close()
