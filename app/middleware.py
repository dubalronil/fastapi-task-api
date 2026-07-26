"""Per-request logging context and the access log."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from app.logging_config import request_id

logger = logging.getLogger("app.access")


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        # Reuse the caller's id when there is one. A proxy or load balancer
        # usually sets this, and keeping it lets one id follow a request across
        # every service that handled it.
        incoming = request.headers.get("x-request-id")
        current_id = incoming or uuid4().hex[:12]
        # No reset token: each request runs in its own task with its own copy
        # of the context, so this cannot leak into another request.
        request_id.set(current_id)

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # error(), not exception(): the handler in errors.py already logs
            # the traceback. All we add is the access line, so a failed request
            # still appears alongside the successful ones without printing the
            # same stack trace twice.
            logger.error(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": _elapsed_ms(started),
                },
            )
            raise

        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": _elapsed_ms(started),
            },
        )
        response.headers["X-Request-ID"] = current_id
        return response


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)
