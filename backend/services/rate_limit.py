"""Minimal in-memory sliding-window rate limiter (hackathon-sufficient).

Applied to the money-adjacent surfaces (/api/payment/*, /api/checkout/*).
Not distributed-safe (per-process memory) - documented in README.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_windows: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()
WINDOW_SECONDS = 60.0


def limit(scope: str, max_per_minute: int):
    """FastAPI dependency: at most max_per_minute requests per client IP
    per scope within a rolling 60s window. Raises 429 with Retry-After."""

    async def _check(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = (scope, client_ip)
        now = time.monotonic()
        with _lock:
            window = _windows[key]
            while window and now - window[0] > WINDOW_SECONDS:
                window.popleft()
            if len(window) >= max_per_minute:
                retry_after = int(WINDOW_SECONDS - (now - window[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for {scope} ({max_per_minute}/min). Retry later.",
                    headers={"Retry-After": str(retry_after)},
                )
            window.append(now)

    return _check


def reset_for_tests():
    """Clear all windows (tests only)."""
    with _lock:
        _windows.clear()
