"""Creates the app and mounts the routers.

Run it with:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from app.routers import tasks

# No create_all() here. Alembic owns the schema, so tables come from
# `alembic upgrade head` rather than from starting the app.

app = FastAPI(title="Task API")

app.include_router(tasks.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
