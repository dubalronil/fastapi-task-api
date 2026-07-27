"""Per-client request limits.

Stops one caller filling the database or running up hosting costs. It is not a
defence against a determined attacker, who can rotate addresses; it caps casual
abuse and runaway loops.

A fixed window per client: count requests, reset the count when the window
rolls over. Counters live in memory, which means they reset on restart and each
instance counts separately, so N replicas allow N times the limit. Both are
acceptable for one instance and would need a shared store to fix.
"""

import logging
import time
from functools import lru_cache

from fastapi import FastAPI, Request

from app.config import settings
from app.errors import error_response

logger = logging.getLogger(__name__)

_PERIOD_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

# Health checks must never be throttled: the platform polls this to decide
# whether the instance is alive, and a 429 would get a healthy app restarted.
EXEMPT_PATHS = frozenset({"/"})

# Bounds memory when many distinct clients appear. Expired entries are cleared
# only once the table grows, rather than scanning it on every request.
_MAX_TRACKED_CLIENTS = 10_000


@lru_cache(maxsize=8)
def parse_limit(value: str) -> tuple[int, int]:
    """Turn "60/minute" into (60, 60) — a count and a window in seconds."""
    count, _, period = value.partition("/")
    period = period.strip().lower().rstrip("s")
    if period not in _PERIOD_SECONDS:
        raise ValueError(f"unknown rate limit period: {value!r}")
    return int(count), _PERIOD_SECONDS[period]


def client_address(request: Request) -> str:
    """Identify the caller.

    Behind a proxy, request.client.host is the proxy's address, so every
    visitor would share one bucket and a single abuser would throttle everyone.
    The caller's address is in X-Forwarded-For instead.

    The rightmost entry is used, not the leftmost. Each proxy appends the
    address it saw, so the last one was observed by our own proxy while earlier
    entries came from the caller and can be forged. Reading the leftmost would
    let anyone dodge the limit with a made-up header.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def register_rate_limiting(app: FastAPI) -> None:
    # client -> (window number, requests seen in that window)
    counters: dict[str, tuple[int, int]] = {}

    @app.middleware("http")
    async def enforce_rate_limit(request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Read per request rather than captured at registration, so the limit
        # can be changed without rebuilding the app. parse_limit is cached, so
        # this costs a dict lookup.
        max_requests, window_seconds = parse_limit(settings.rate_limit)

        now = time.monotonic()
        window = int(now // window_seconds)
        client = client_address(request)

        # No lock: this runs on the event loop and does not await between
        # reading and writing, so no other request can interleave here.
        seen_window, count = counters.get(client, (window, 0))
        count = count + 1 if seen_window == window else 1
        counters[client] = (window, count)

        if len(counters) > _MAX_TRACKED_CLIENTS:
            for key, (client_window, _) in list(counters.items()):
                if client_window < window:
                    del counters[key]

        if count > max_requests:
            logger.warning(
                "rate limit exceeded",
                extra={"client": client, "path": request.url.path},
            )
            retry_after = int((window + 1) * window_seconds - now) + 1
            return error_response(
                429,
                "Too many requests, please slow down",
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
