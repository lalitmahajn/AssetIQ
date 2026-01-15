from __future__ import annotations
import asyncio
import json
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

@dataclass
class SseEvent:
    id: str
    data_json: str

class SseBus:
    def __init__(self, maxlen: int = 5000):
        self._events: list[SseEvent] = []
        self._maxlen = maxlen
        self._cond = asyncio.Condition()

    def publish(self, data: dict) -> None:
        ev_id = str(int(time.time() * 1000))
        ev = SseEvent(id=ev_id, data_json=json.dumps(data, ensure_ascii=False))
        self._events.append(ev)
        if len(self._events) > self._maxlen:
            self._events = self._events[-self._maxlen:]
        async def _notify():
            async with self._cond:
                self._cond.notify_all()
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_notify())
        except RuntimeError:
            # no loop: ignore (unit context)
            pass

    async def subscribe(self, last_event_id: Optional[str]) -> AsyncIterator[SseEvent]:
        start_idx = len(self._events) # default: live only
        if last_event_id:
            for i, ev in enumerate(self._events):
                if ev.id == last_event_id:
                    start_idx = i + 1
                    break
            # If ID not found (stale), maybe we should replay partial or none? 
            # Current logic defaults to live if ID not found because start_idx=len.
            # But wait, original code iterated from start_idx=0 if ID not found in loop. 
            # Let's logic check:
            # If last_event_id is 'ABC' and not in list (expired), loop finishes, start_idx remains len(events).
            # This is safe (gap in data -> user misses old events, but better than replaying 5000).
            pass

        # replay existing
        for ev in self._events[start_idx:]:
            yield ev

        # live
        while True:
            async with self._cond:
                await self._cond.wait()
            # after wake: yield newest batch
            for ev in self._events[-50:]:
                if last_event_id and ev.id <= last_event_id:
                    continue
                yield ev
                last_event_id = ev.id
