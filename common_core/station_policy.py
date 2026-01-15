from __future__ import annotations

ALLOWED_PREFIXES = (
    "/ingest/",
    "/realtime/stop-events",
    "/stations/config",
)

def station_allowed(path: str) -> bool:
    return any(path.startswith(p) for p in ALLOWED_PREFIXES)
