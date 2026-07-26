from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite refuses connections shared between threads, which breaks FastAPI's
    # threadpool. Postgres rejects options it doesn't recognise, so this can
    # only be passed when we are actually on SQLite.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

# A factory that produces database sessions, one per request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class our table models inherit from.
Base = declarative_base()


def get_db():
    # Opens a fresh session for each request and closes it afterwards, even if
    # the request errored. Tests override this to point at a test database.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lives here next to get_db so every route spells the dependency the same way.
DbSession = Annotated[Session, Depends(get_db)]
