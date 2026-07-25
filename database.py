from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The database URL. For SQLite it's just a file path — tasks.db will be
# created in the project folder. The three slashes then the path is the format.
SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"

# The engine is the core connection to the database.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# A factory that produces database sessions (one per request, later).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class our table models will inherit from.
Base = declarative_base()
