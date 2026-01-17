from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class Bucket:
    tokens: float
    updated_at: float
    blocked_until: float


class RateLimiter:
    def __init__(self, capacity: int, refill_per_sec: float, block_seconds: int) -> None:
        self.capacity = float(capacity)
        self.refill_per_sec = float(refill_per_sec)
        self.block_seconds = int(block_seconds)
        self._lock = Lock()
        self._buckets: dict[tuple[str, str], Bucket] = {}

    def allow(self, ip: str, key: str) -> bool:
        now = time.time()
        k = (ip or "unknown", key or "unknown")
        with self._lock:
            b = self._buckets.get(k)
            if not b:
                b = Bucket(tokens=self.capacity, updated_at=now, blocked_until=0.0)
                self._buckets[k] = b

            if now < b.blocked_until:
                return False

            elapsed = max(0.0, now - b.updated_at)
            b.tokens = min(self.capacity, b.tokens + elapsed * self.refill_per_sec)
            b.updated_at = now

            if b.tokens >= 1.0:
                b.tokens -= 1.0
                return True

            b.blocked_until = now + self.block_seconds
            return False


login_limiter = RateLimiter(capacity=5, refill_per_sec=0.1, block_seconds=60)
