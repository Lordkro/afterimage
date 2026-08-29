from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindow:
    def __init__(self, *, max_hits: int, window_s: float) -> None:
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self._hits[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.max_hits:
            return False
        q.append(now)
        return True
