import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import Base
from main import app, get_db

# A separate database used ONLY for tests — never touches tasks.db.
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"
test_engine = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
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

client = TestClient(app)


# autouse=True runs this around EVERY test automatically: fresh empty
# tables before, wiped clean after — so tests never affect each other.
@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_task():
    response = client.post("/tasks", json={"title": "Write tests"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write tests"
    assert data["completed"] is False
    assert data["id"] == 1  # first task in a fresh db


def test_list_tasks_starts_empty():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []  # fresh db, no tasks yet


def test_filter_by_completed():
    client.post("/tasks", json={"title": "Done task", "completed": True})
    client.post("/tasks", json={"title": "Todo task", "completed": False})

    response = client.get("/tasks?completed=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Done task"


def test_pagination_limit():
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    response = client.get("/tasks?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_pagination_skip():
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    # Skip the first two, so only the third comes back.
    response = client.get("/tasks?skip=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Task 2"


def test_get_one_task():
    created = client.post("/tasks", json={"title": "Find me"}).json()
    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_get_missing_task_returns_404():
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_update_task():
    created = client.post("/tasks", json={"title": "Old title"}).json()
    response = client.put(
        f"/tasks/{created['id']}",
        json={"title": "New title", "completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["completed"] is True
    assert data["id"] == created["id"]  # id must not change


def test_delete_task():
    created = client.post("/tasks", json={"title": "Delete me"}).json()
    response = client.delete(f"/tasks/{created['id']}")
    assert response.status_code == 200

    # After deleting, fetching it should 404.
    assert client.get(f"/tasks/{created['id']}").status_code == 404
