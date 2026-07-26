from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    # SQLite only. It normally refuses connections shared between threads,
    # which breaks FastAPI's threadpool. Remove this when we move to Postgres.
    connect_args={"check_same_thread": False},
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
