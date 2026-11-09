"""Sliding-window counter in memory."""
from collections import defaultdict, deque
from datetime import timedelta

from app.core import clock

# ponytail: per-process memory; use a shared store (Redis) if the API is replicated.
_hits: dict[str, deque] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def _trim(key: str, window: timedelta) -> deque:
    q, cutoff = _hits[key], clock.now() - window
    while q and q[0] <= cutoff:
        q.popleft()
    return q


def blocked(key: str, limit: int, window: timedelta) -> bool:
    """True when `limit` hits are already recorded in the window (does not record one)."""
    return len(_trim(key, window)) >= limit


def hit(key: str, window: timedelta) -> None:
    _trim(key, window).append(clock.now())


def take(key: str, limit: int, window: timedelta) -> bool:
    """Record a hit unless over the limit. Returns False when over."""
    if blocked(key, limit, window):
        return False
    hit(key, window)
    return True
