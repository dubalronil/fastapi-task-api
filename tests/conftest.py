import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 — imported so its table registers on Base
from app.config import settings
from app.database import Base, get_db
from app.main import app

# The whole suite shares one client address, so the real limit would throttle
# the tests themselves. Rate limiting is covered in test_rate_limit.py, which
# builds its own app at a deliberately low limit.
settings.rate_limit = "1000000/minute"

# Separate databases from the one the app uses, on the same Postgres container.
# Tests run on the same engine as production, so engine-specific behaviour
# (ordering, types, constraints) is exercised rather than assumed.
_DEFAULT = "postgresql+psycopg://tasks:tasks@localhost:5432/tasks_test"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", _DEFAULT)

# Derived by setting the database name, not by string replacement: with an
# overridden TEST_DATABASE_URL a replace can silently produce the same URL, and
# the migration test would then DROP SCHEMA on the database everything else is
# using. Naming it explicitly makes that impossible.
_test_url = make_url(TEST_DATABASE_URL)
MIGRATION_DATABASE_URL = _test_url.set(
    database=f"{_test_url.database}_migrations"
).render_as_string(hide_password=False)


def ensure_database(url: str) -> None:
    """Create the database named in `url` if it does not exist yet."""
    target = make_url(url)
    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT, and it
    # has to be issued from a different database — "postgres" always exists.
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": target.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()


ensure_database(TEST_DATABASE_URL)
ensure_database(MIGRATION_DATABASE_URL)

test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def schema():
    # Built once for the whole run instead of once per test. Correctness comes
    # from rolling each test back, not from rebuilding the tables.
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """A session whose writes are thrown away when the test finishes.

    The trick is the outer transaction. Everything the test does happens inside
    it, and rolling it back at the end undoes the lot without any DDL.

    join_transaction_mode="create_savepoint" is what makes that survive the
    commits our endpoints do: the session joins the open transaction by opening
    a SAVEPOINT, so db.commit() releases that savepoint and starts a new one
    rather than committing for real. The outer rollback still wins.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )

    # Every request in this test gets this same session, so writes made by the
    # endpoints and by the test itself are visible to each other.
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        # pop, not clear: clearing would also remove any other override a test
        # happened to install.
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def backdate(db_session):
    # Pushes a row's timestamps into the past. It has to run on the test's own
    # session: a separate connection would not see rows that only exist inside
    # this test's uncommitted transaction.
    def _backdate(task_id: int, when: str = "2020-01-01 00:00:00+00"):
        db_session.execute(
            text("UPDATE tasks SET created_at = :w, updated_at = :w WHERE id = :i"),
            {"w": when, "i": task_id},
        )
        db_session.commit()

    return _backdate
