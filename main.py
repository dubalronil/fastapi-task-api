from fastapi import FastAPI

import models  # noqa: F401 — imported so its table registers on Base
from database import engine, Base
from routers import tasks

# Create tables in the database if they don't already exist.
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Plug the tasks router into the app. Every route in routers/tasks.py
# is now live under its /tasks prefix.
app.include_router(tasks.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
