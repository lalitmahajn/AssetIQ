from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from common_core.security import verify_jwt


def get_actor(request: Request):
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="MISSING_TOKEN")
    token = auth.split(" ", 1)[1].strip()
    return verify_jwt(token)


def require_roles(*roles: str):
    def _dep(claims=Depends(get_actor)):
        user_roles = set(claims.get("roles", []) or [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        return claims

    return _dep
