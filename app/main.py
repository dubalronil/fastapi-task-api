"""Creates the app and mounts the routers.

Run it with:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from app import models  # noqa: F401 — imported so its table registers on Base
from app.database import Base, engine
from app.routers import tasks

# Creates missing tables only. It never adds columns to a table that already
# exists, so changing models.py means rebuilding the database until we add Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task API")

app.include_router(tasks.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
