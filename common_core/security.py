from __future__ import annotations

import time
from typing import Any

import jwt

from common_core.config import settings


def issue_jwt(sub: str, roles: list[str]) -> str:
    now = int(time.time())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + settings.jwt_ttl_minutes * 60,
        "sub": sub,
        "roles": roles,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
