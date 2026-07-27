"""API key check for the endpoints that change data.

Reads stay public so the API can be browsed and demonstrated. Writes need a
shared key, which keeps a public deployment from being filled with whatever
strangers feel like posting.

This is a gate, not authentication: there are no users and the key says nothing
about who is calling. Anyone holding it can write.
"""

import logging
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import settings

logger = logging.getLogger(__name__)

# auto_error=False so a missing header reaches our own check and produces the
# standard error shape rather than FastAPI's default.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: Annotated[str | None, Depends(_api_key_header)]) -> None:
    if settings.api_key is None:
        # Unset means an unprotected deployment, which is fine locally and a
        # mistake in production. warn_if_unprotected() says so at startup.
        return

    # compare_digest rather than ==, so the time taken does not depend on how
    # many characters matched. A plain comparison leaks the key one character
    # at a time to anyone willing to measure.
    if not provided or not secrets.compare_digest(provided, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def warn_if_unprotected() -> None:
    if settings.api_key is None:
        logger.warning(
            "API_KEY is not set — write endpoints are open to anyone. "
            "Set it for any deployment that is reachable publicly."
        )


# Documents the 401 in the OpenAPI schema for the routes that require the key.
API_KEY_RESPONSE: dict[int | str, dict] = {
    401: {"description": "Missing or invalid API key"}
}
