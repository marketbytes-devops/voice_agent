from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Sliding window in-memory rate limiter to protect sensitive endpoints
    (auth login, webhook ingestion, slot calculations) from brute force and denial of service.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def __call__(self, request: Request) -> None:
        client_key = self._get_client_key(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds

        async with self._lock:
            q = self._history[client_key]
            # Evict timestamps outside the sliding window
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= self.max_requests:
                oldest = q[0]
                retry_after = int(self.window_seconds - (now - oldest)) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down and try again later.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            q.append(now)


# Standard reusable limiters
auth_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
api_rate_limiter = SlidingWindowRateLimiter(max_requests=120, window_seconds=60)
