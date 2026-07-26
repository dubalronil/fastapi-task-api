"""Creates the app and mounts the routers.

Run it with:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

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
def health_check():
    return {"status": "ok"}
