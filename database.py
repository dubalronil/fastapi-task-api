from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# The database URL now comes from config (which reads .env), instead of
# being hardcoded here. Swap environments by changing .env, not the code.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

# A factory that produces database sessions (one per request, later).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class our table models will inherit from.
Base = declarative_base()
