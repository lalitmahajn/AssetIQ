from __future__ import annotations
import bcrypt



def _validate_pin(pin: str) -> None:
    if not pin:
        raise ValueError("PIN is required")
    if not pin.isdigit():
        raise ValueError("PIN must be numeric digits only")
    if len(pin) < 6:
        raise ValueError("PIN must be at least 6 digits")

def hash_pin(pin: str) -> str:
    _validate_pin(pin)
    salt = bcrypt.gensalt(rounds=12)
    h = bcrypt.hashpw(pin.encode("utf-8"), salt)
    return h.decode("utf-8")

def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))
    except Exception:
        return False
