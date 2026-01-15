from __future__ import annotations
import bcrypt

_WEAK_PINS = {"0000","1111","2222","3333","4444","5555","6666","7777","8888","9999","1234","12345","123456","000000","111111"}

def _validate_pin(pin: str) -> None:
    if not pin:
        raise ValueError("PIN is required")
    if len(pin) < 6:
        raise ValueError("PIN must be at least 6 chars")
    if pin.strip() in _WEAK_PINS:
        raise ValueError("PIN is too weak")
    # Allow numeric or mixed; if numeric, require at least 6 digits.
    if pin.isdigit() and len(pin) < 6:
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
