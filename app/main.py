"""Creates the app and mounts the routers.

Run it with:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import DbSession
from app.errors import register_error_handlers
from app.logging_config import configure_logging
from app.middleware import register_middleware
from app.routers import tasks

# Before the app exists, so startup messages use our format too.
configure_logging()

# No create_all() here. Alembic owns the schema, so tables come from
# `alembic upgrade head` rather than from starting the app.

app = FastAPI(title="Task API")

register_error_handlers(app)
register_middleware(app)

# Named origins rather than "*": a wildcard cannot be combined with credentials
# later, and listing them keeps the allowed callers visible in config.
#
# expose_headers is the part that is easy to miss. A browser only lets page
# scripts read a short list of response headers unless the server names others,
# so without this the frontend could not read X-Request-ID and could not quote
# it when reporting a problem.
#
# Known gap: unhandled 500s do not get these headers. Starlette handles them in
# a middleware that sits outside every user middleware, so nothing here can
# wrap it, and a browser reports such a response as a CORS failure rather than
# a 500. Worth recognising while debugging; not worth special-casing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(tasks.router)


@app.get("/")
def health_check(db: DbSession):
    # Deployment platforms use this to decide whether to send traffic here, so
    # it has to fail when the app cannot actually serve requests. Checking only
    # that the process is alive would report healthy while every request 500s.
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}
