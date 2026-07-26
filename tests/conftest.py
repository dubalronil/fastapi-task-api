import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 — imported so its table registers on Base
from app.database import Base, get_db
from app.main import app

# A separate database used ONLY for tests — never touches tasks.db.
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# The test version of get_db: hands out sessions bound to the TEST database.
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI to use override_get_db wherever the app asks for get_db.
app.dependency_overrides[get_db] = override_get_db


# autouse=True runs this around EVERY test automatically: fresh empty
# tables before, wiped clean after — so tests never affect each other.
@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def backdate():
    # Pushes a row's timestamps into the past. Used instead of time.sleep()
    # because SQLite only tracks whole seconds, so an update straight after an
    # insert lands in the same second and looks like nothing changed.
    def _backdate(task_id: int, when: str = "2020-01-01 00:00:00"):
        with test_engine.begin() as conn:
            conn.execute(
                text("UPDATE tasks SET created_at = :w, updated_at = :w WHERE id = :i"),
                {"w": when, "i": task_id},
            )

    return _backdate
