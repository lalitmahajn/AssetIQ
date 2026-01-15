from __future__ import annotations

ROLE_PERMS: dict[str, set[str]] = {
    "operator": {"stop.view", "ticket.view"},
    "maintenance": {"stop.view", "stop.resolve", "ticket.view", "ticket.create", "ticket.close", "insight.view"},
    "supervisor": {"stop.view", "stop.resolve", "ticket.view", "ticket.create", "ticket.close", "ticket.assign", "masters.approve"},
    "admin": {"*"},
    "hq_viewer": {"insight.view", "hq.view", "report.view"},
}

def has_perm(roles: list[str], perm: str) -> bool:
    for r in roles:
        perms = ROLE_PERMS.get(r, set())
        if "*" in perms or perm in perms:
            return True
    return False
