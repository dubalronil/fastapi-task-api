"""Bad input is rejected with a 422 before the endpoint ever runs."""


# ---- Request body ----


def test_create_rejects_empty_title(client):
    response = client.post("/tasks", json={"title": ""})
    assert response.status_code == 422
    # FastAPI tells the client exactly which field failed.
    assert response.json()["errors"][0]["field"] == "body.title"


def test_create_rejects_whitespace_only_title(client):
    # Stripped to "" first, then min_length rejects it.
    assert client.post("/tasks", json={"title": "   "}).status_code == 422


def test_create_strips_surrounding_whitespace(client):
    response = client.post("/tasks", json={"title": "  Buy milk  "})
    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"


def test_create_rejects_overlong_title(client):
    assert client.post("/tasks", json={"title": "x" * 201}).status_code == 422


def test_create_accepts_title_at_max_length(client):
    # Check both sides of the limit, since 200 is allowed and 201 is not.
    assert client.post("/tasks", json={"title": "x" * 200}).status_code == 201


def test_create_rejects_overlong_description(client):
    response = client.post("/tasks", json={"title": "ok", "description": "x" * 2001})
    assert response.status_code == 422


def test_rejected_task_is_never_written(client):
    # Validation runs first, so create_task never ran and nothing was saved.
    client.post("/tasks", json={"title": ""})
    assert client.get("/tasks").json() == []


# ---- PATCH ----


def test_patch_rejects_null_title(client):
    # The title column is NOT NULL, so without the validator this would be a 500.
    created = client.post("/tasks", json={"title": "Keep me"}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": None})
    assert response.status_code == 422
    assert client.get(f"/tasks/{created['id']}").json()["title"] == "Keep me"


def test_patch_enforces_the_same_constraints_as_create(client):
    created = client.post("/tasks", json={"title": "Keep me"}).json()
    url = f"/tasks/{created['id']}"

    assert client.patch(url, json={"title": ""}).status_code == 422
    assert client.patch(url, json={"title": "x" * 201}).status_code == 422


# ---- Query params ----


def test_list_rejects_negative_skip(client):
    assert client.get("/tasks?skip=-1").status_code == 422


def test_list_rejects_zero_limit(client):
    assert client.get("/tasks?limit=0").status_code == 422


def test_list_rejects_limit_above_ceiling(client):
    assert client.get("/tasks?limit=101").status_code == 422


def test_list_accepts_limit_at_ceiling(client):
    assert client.get("/tasks?limit=100").status_code == 200


# ---- Path params ----


def test_rejects_non_positive_task_id(client):
    assert client.get("/tasks/0").status_code == 422
    assert client.get("/tasks/-3").status_code == 422
