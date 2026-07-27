"""One error shape for the whole API.

Every failure comes back with the same keys, whether it is a 404 we raised, a
422 from validation, a 405 from Starlette, or an unhandled crash. A client then
needs one code path for errors instead of one per kind. The shape follows
RFC 9457 (Problem Details), trimmed to the fields this API actually uses.

    {"status": 404, "title": "Not Found", "detail": "Task not found"}

Validation failures add an `errors` list so the client can point at the field.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import request_id

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: int
    title: str
    detail: str
    request_id: str
    errors: list[FieldError] | None = None


# Attached to the routes so /openapi.json describes the errors we actually
# send. Without this FastAPI documents its own default 422 shape, which stopped
# being true once these handlers took over.
ERROR_RESPONSES: dict[int | str, dict] = {
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}
NOT_FOUND_RESPONSE: dict[int | str, dict] = {
    404: {"model": ErrorResponse, "description": "Task not found"}
}


def error_response(
    status_code: int,
    detail: str,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    try:
        title = HTTPStatus(status_code).phrase
    except ValueError:  # a status code outside the standard set
        title = "Error"

    current_id = request_id.get()
    body = ErrorResponse(
        status=status_code,
        title=title,
        detail=detail,
        # The same id is on every log line for this request, so a user quoting
        # it from an error message is enough to find what actually happened.
        request_id=current_id,
        errors=errors,
    )
    # exclude_none keeps `errors` out of responses that have no field detail.
    # Headers the exception carried (a 405's Allow, a 401's WWW-Authenticate)
    # are forwarded; ours goes last so the request id stays authoritative.
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers={**(headers or {}), "X-Request-ID": current_id},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        # Catches both the HTTPExceptions we raise and the ones Starlette
        # raises itself, so an unmatched URL looks like every other error.
        return error_response(exc.status_code, str(exc.detail), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        errors = [
            FieldError(
                field=".".join(str(part) for part in err["loc"]), message=err["msg"]
            )
            for err in exc.errors()
        ]
        return error_response(422, "Request validation failed", errors)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # Anything that reaches here is our bug, not the client's. Log the real
        # exception and send back nothing that describes our internals.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error")
