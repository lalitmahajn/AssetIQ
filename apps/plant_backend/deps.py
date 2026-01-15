from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from common_core.security import verify_jwt
from common_core.rbac import has_perm

bearer = HTTPBearer(auto_error=False)

def get_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(status_code=401, detail="AUTH_REQUIRED")
    try:
        claims = verify_jwt(creds.credentials)
        roles = claims.get("roles", [])
        return {"sub": claims.get("sub"), "roles": roles}
    except Exception:
        raise HTTPException(status_code=401, detail="AUTH_INVALID")

def require_perm(perm: str):
    def _inner(user=Depends(get_user)):
        if not has_perm(user["roles"], perm):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        return user
    return _inner
