from __future__ import annotations

# Minimal schemas required for HQ Phase-2 visibility (read-only)

REQUIRED_KEYS = {
    "timeline_event": {"site_code", "entity_id", "event_type", "occurred_at_utc"},
    "ticket": {"site_code", "entity_id", "asset_id", "status", "created_at_utc"},
    "rollup": {"site_code", "entity_id", "day_utc"},
}

OPTIONAL_KEYS = {
    "rollup": {"stops", "faults", "tickets_open", "sla_breaches", "downtime_minutes"},
    "ticket": {"title", "priority", "sla_due_at_utc", "acknowledged_at_utc", "resolved_at_utc"},
    "timeline_event": {"asset_id", "reason_code", "duration_seconds"},
}


def validate_entity(entity_type: str, payload: dict) -> None:
    need = REQUIRED_KEYS.get(entity_type)
    if not need:
        raise ValueError(f"Unknown entity_type: {entity_type}")

    missing = [k for k in need if k not in payload or payload.get(k) in (None, "")]
    if missing:
        raise ValueError(f"Missing keys for {entity_type}: {missing}")
