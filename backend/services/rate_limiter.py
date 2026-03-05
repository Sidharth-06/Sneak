"""
Sliding-window rate limiter for OpenRouter API calls.

Free models on OpenRouter allow roughly 6-20 req/min (varies by model/load).
We gate conservatively at 4 req/min (one every 15 s) to stay well under limits.
Requests are serialised — no request is ever dropped, they just wait in line.

The asyncio.Lock is created lazily on first use so it always binds to
the running event loop (avoids "Future attached to a different loop" errors
with uvicorn --reload).
"""

import asyncio
import time

class RateLimiter:
    def __init__(self, max_calls: int = 4, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self.min_interval = period_seconds / max_calls   # min seconds between calls
        self._lock: asyncio.Lock | None = None           # created lazily
        self._timestamps: list[float] = []              # sliding window of call times

    def _get_lock(self) -> asyncio.Lock:
        """Return (creating if needed) a lock bound to the current event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self):
        """Block until it is safe to make the next API call."""
        lock = self._get_lock()
        async with lock:
            now = time.monotonic()

            # Evict timestamps outside the rolling window
            self._timestamps = [t for t in self._timestamps if now - t < self.period]

            if len(self._timestamps) >= self.max_calls:
                # Window is full — wait until the oldest entry expires
                oldest = self._timestamps[0]
                wait = self.period - (now - oldest) + 0.2   # tiny safety buffer
                print(f"[RateLimiter] Window full ({len(self._timestamps)}/{self.max_calls}). Waiting {wait:.1f}s…")
                await asyncio.sleep(wait)
                # Re-evict after sleep
                self._timestamps = [t for t in self._timestamps if time.monotonic() - t < self.period]
            else:
                # Enforce minimum spacing between consecutive calls
                if self._timestamps:
                    since_last = time.monotonic() - self._timestamps[-1]
                    if since_last < self.min_interval:
                        gap = self.min_interval - since_last + 0.1
                        print(f"[RateLimiter] Spacing gap {gap:.1f}s…")
                        await asyncio.sleep(gap)

            self._timestamps.append(time.monotonic())
            print(f"[RateLimiter] Slot granted. Window: {len(self._timestamps)}/{self.max_calls}")


# Single shared instance used by the whole process
openrouter_limiter = RateLimiter(max_calls=3, period_seconds=60.0)
