"""Creates the app and mounts the routers.

Run it with:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
