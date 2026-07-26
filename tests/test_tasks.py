def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---- Create and read ----


def test_create_task(client):
    response = client.post("/tasks", json={"title": "Write tests"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write tests"
    assert data["completed"] is False
    assert data["id"] == 1  # first task in a fresh db


def test_list_tasks_starts_empty(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_one_task(client):
    created = client.post("/tasks", json={"title": "Find me"}).json()
    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_get_missing_task_returns_404(client):
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ---- Filtering and pagination ----


def test_filter_by_completed(client):
    client.post("/tasks", json={"title": "Done task", "completed": True})
    client.post("/tasks", json={"title": "Todo task", "completed": False})

    data = client.get("/tasks?completed=true").json()
    assert len(data) == 1
    assert data[0]["title"] == "Done task"


def test_pagination_limit(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    assert len(client.get("/tasks?limit=2").json()) == 2


def test_pagination_skip(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    # Skip the first two, so only the third comes back.
    data = client.get("/tasks?skip=2").json()
    assert len(data) == 1
    assert data[0]["title"] == "Task 2"


def test_pagination_order_is_deterministic(client):
    # Pages only mean something if the underlying order is fixed. SQLite
    # happens to return insertion order even without ORDER BY, so this pins
    # the contract for engines like Postgres that guarantee nothing.
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})

    first_page = client.get("/tasks?limit=3").json()
    second_page = client.get("/tasks?skip=3&limit=3").json()

    ids = [task["id"] for task in first_page + second_page]
    assert ids == sorted(ids)  # ascending id order
    assert len(set(ids)) == 5  # no row skipped or repeated across the pages


# ---- PUT replaces the whole task ----


def test_put_replaces_entire_task(client):
    created = client.post("/tasks", json={"title": "Old title"}).json()

    response = client.put(
        f"/tasks/{created['id']}",
        json={
            "title": "New title",
            "description": "now with detail",
            "completed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["description"] == "now with detail"
    assert data["completed"] is True
    assert data["id"] == created["id"]  # id must not change


def test_put_rejects_incomplete_body(client):
    created = client.post(
        "/tasks", json={"title": "Ship it", "description": "by Friday"}
    ).json()

    response = client.put(
        f"/tasks/{created['id']}", json={"title": "Ship it", "completed": True}
    )
    assert response.status_code == 422
    assert client.get(f"/tasks/{created['id']}").json()["description"] == "by Friday"


def test_put_can_explicitly_null_the_description(client):
    created = client.post(
        "/tasks", json={"title": "Ship it", "description": "by Friday"}
    ).json()

    response = client.put(
        f"/tasks/{created['id']}",
        json={"title": "Ship it", "description": None, "completed": False},
    )
    assert response.status_code == 200
    assert response.json()["description"] is None


# ---- PATCH only touches what was sent ----


def test_patch_leaves_unmentioned_fields_alone(client):
    created = client.post(
        "/tasks", json={"title": "Ship it", "description": "by Friday"}
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"completed": True})
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["title"] == "Ship it"
    assert data["description"] == "by Friday"


def test_patch_updates_a_single_field(client):
    created = client.post("/tasks", json={"title": "Typo"}).json()
    response = client.patch(f"/tasks/{created['id']}", json={"title": "Fixed"})
    assert response.status_code == 200
    assert response.json()["title"] == "Fixed"


def test_patch_explicit_null_clears_nullable_field(client):
    # Sending null is different from leaving the field out.
    created = client.post(
        "/tasks", json={"title": "Ship it", "description": "by Friday"}
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_empty_body_is_a_noop(client):
    created = client.post("/tasks", json={"title": "Unchanged"}).json()
    response = client.patch(f"/tasks/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json() == created


def test_patch_missing_task_returns_404(client):
    assert client.patch("/tasks/999", json={"title": "Ghost"}).status_code == 404


# ---- Delete ----


def test_delete_task(client):
    created = client.post("/tasks", json={"title": "Delete me"}).json()
    response = client.delete(f"/tasks/{created['id']}")
    assert response.status_code == 204
    assert response.text == ""  # 204 means no body at all

    # After deleting, fetching it should 404.
    assert client.get(f"/tasks/{created['id']}").status_code == 404


# ---- Timestamps ----


def test_timestamps_are_set_on_create(client):
    data = client.post("/tasks", json={"title": "Timed"}).json()
    assert data["created_at"] is not None
    # A new task has never been modified, so both are the same.
    assert data["created_at"] == data["updated_at"]


def test_timestamps_cannot_be_set_by_the_client(client):
    data = client.post(
        "/tasks",
        json={
            "title": "Nice try",
            "created_at": "1999-01-01T00:00:00",
            "updated_at": "1999-01-01T00:00:00",
        },
    ).json()
    assert not data["created_at"].startswith("1999")


def test_updated_at_moves_on_patch(client, backdate):
    created = client.post("/tasks", json={"title": "Move me"}).json()
    backdate(created["id"])

    patched = client.patch(f"/tasks/{created['id']}", json={"completed": True}).json()

    assert not patched["updated_at"].startswith("2020")
    assert patched["created_at"].startswith("2020")  # created_at must not move


def test_updated_at_moves_on_put(client, backdate):
    created = client.post("/tasks", json={"title": "Replace me"}).json()
    backdate(created["id"])

    replaced = client.put(
        f"/tasks/{created['id']}",
        json={"title": "Replaced", "description": None, "completed": True},
    ).json()

    assert not replaced["updated_at"].startswith("2020")


def test_empty_patch_leaves_updated_at_alone(client, backdate):
    created = client.post("/tasks", json={"title": "Still"}).json()
    backdate(created["id"])

    # Nothing was assigned, so no UPDATE is sent and onupdate never fires.
    patched = client.patch(f"/tasks/{created['id']}", json={}).json()
    assert patched["updated_at"].startswith("2020")


def test_patch_with_an_identical_value_leaves_updated_at_alone(client, backdate):
    created = client.post("/tasks", json={"title": "Same"}).json()
    backdate(created["id"])

    # The field was assigned, but SQLAlchemy sees the value didn't change and
    # skips the UPDATE.
    patched = client.patch(f"/tasks/{created['id']}", json={"title": "Same"}).json()
    assert patched["updated_at"].startswith("2020")
