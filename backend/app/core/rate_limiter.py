from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class InMemoryRateLimiter:
    """Sliding-window rate limiter backed by an in-memory deque.

    Shared across LlmService and FeishuService.  Two modes:
    - ``acquire()`` raises ``RuntimeError`` when the window is full (LLM path).
    - ``wait_and_acquire()`` blocks until a slot is available (Feishu sync path).
    """

    def __init__(
        self,
        limit: int,
        *,
        window_seconds: int = 60,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.limit = max(limit, 1)
        self.window_seconds = window_seconds
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self.events: deque[float] = deque()

    def _purge(self, now: float) -> None:
        while self.events and now - self.events[0] >= self.window_seconds:
            self.events.popleft()

    def acquire(self) -> None:
        """Acquire a slot or raise ``RuntimeError`` immediately."""
        now = self.clock()
        self._purge(now)
        if len(self.events) >= self.limit:
            raise RuntimeError(
                f'Rate limit reached ({len(self.events)}/{self.limit} requests per {self.window_seconds}s window).'
            )
        self.events.append(now)

    def wait_and_acquire(self) -> None:
        """Block until a slot is available, then acquire it."""
        while True:
            now = self.clock()
            self._purge(now)
            if len(self.events) < self.limit:
                self.events.append(now)
                return
            # Sleep until the oldest event expires
            wait_time = self.window_seconds - (now - self.events[0])
            if wait_time > 0:
                self.sleeper(wait_time)
