from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from common_core.config import settings


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _sign(secret: str, body: bytes) -> bytes:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()


def sign_download_token(site_code: str, rel_path: str, ttl_seconds: int = 3600) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    payload = {
        "kid": settings.sync_hmac_kid,
        "site_code": site_code,
        "rel_path": rel_path,
        "exp": exp,
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = _sign(settings.sync_hmac_secret, body)
    return f"{_b64(body)}.{_b64(sig)}"


def verify_download_token(token: str) -> dict:
    a, b = token.split(".", 1)
    body = _b64d(a)
    sig = _b64d(b)
    ok = hmac.compare_digest(sig, _sign(settings.sync_hmac_secret, body))
    if not ok and settings.sync_hmac_secret_prev:
        ok = hmac.compare_digest(sig, _sign(settings.sync_hmac_secret_prev, body))
    if not ok:
        raise ValueError("bad signature")
    payload = json.loads(body.decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("expired")
    return payload
