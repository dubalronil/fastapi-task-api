"""Every error, whatever caused it, comes back with the same keys."""

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.routers.tasks as tasks_router
from app.main import app

ERROR_KEYS = {"status", "title", "detail", "request_id"}


@pytest.fixture
def unauthorized_route():
    """Adds a route raising a 401 with a custom header, then removes it.

    Registering this at module level would leave it on the shared app object
    for the rest of the run, which is not something a test should do to the
    application it is testing.
    """
    path = "/_test/unauthorized"

    @app.get(path, include_in_schema=False)
    def _raise_unauthorized():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    yield path
    app.router.routes = [
        route for route in app.router.routes if getattr(route, "path", None) != path
    ]


def test_raised_404_uses_the_standard_shape(client):
    body = client.get("/tasks/999").json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["detail"] == "Task not found"


def test_unmatched_route_uses_the_standard_shape(client):
    # Starlette raises this one, not us. It still has to look the same.
    body = client.get("/no-such-endpoint").json()
    assert ERROR_KEYS <= body.keys()
    assert body["status"] == 404


def test_wrong_method_uses_the_standard_shape(client):
    body = client.delete("/").json()
    assert ERROR_KEYS <= body.keys()
    assert body["status"] == 405


def test_405_preserves_the_allow_header(client):
    # RFC 9110 requires a 405 to name the methods that ARE allowed. Starlette
    # attaches the header to the exception; the handler must forward it.
    response = client.delete("/")
    assert response.status_code == 405
    assert "GET" in response.headers["allow"]


def test_custom_exception_headers_are_preserved(client, unauthorized_route):
    # A 401 without WWW-Authenticate is useless — the client never learns how
    # to authenticate. Exception headers ride along with the standard envelope.
    response = client.get(unauthorized_route)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["x-request-id"]  # ours is still there too

    body = response.json()
    assert ERROR_KEYS <= body.keys()
    assert body["detail"] == "Not authenticated"


def test_validation_error_names_the_field(client):
    body = client.post("/tasks", json={"title": ""}).json()
    assert body["status"] == 422
    assert body["detail"] == "Request validation failed"
    assert body["errors"][0]["field"] == "body.title"


def test_query_validation_error_names_the_parameter(client):
    body = client.get("/tasks?limit=999").json()
    assert body["errors"][0]["field"] == "query.limit"


def test_errors_key_is_absent_when_there_are_no_field_errors(client):
    # exclude_none keeps the response clean rather than sending "errors": null.
    assert "errors" not in client.get("/tasks/999").json()


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/tasks/999", None),
        ("get", "/tasks/0", None),
        ("get", "/no-such-endpoint", None),
        ("post", "/tasks", {"title": ""}),
        ("patch", "/tasks/999", {"title": "x"}),
    ],
)
def test_every_error_has_the_same_keys(client, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}
    body = getattr(client, method)(path, **kwargs).json()
    assert ERROR_KEYS <= body.keys()
    assert set(body) <= ERROR_KEYS | {"errors"}


def test_unhandled_exception_returns_500_without_leaking(
    db_session, monkeypatch, caplog
):
    # db_session is what installs the get_db override. Without it this test
    # would build its own client and talk to the real application database.
    def explode(*args, **kwargs):
        raise RuntimeError("connection string: postgres://user:hunter2@db")

    monkeypatch.setattr(tasks_router, "get_task_or_404", explode)

    # raise_server_exceptions=False so the client sees the response a real
    # HTTP client would get, instead of the exception being re-raised here.
    crashing_client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        response = crashing_client.get("/tasks/1")

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == 500
    assert body["title"] == "Internal Server Error"
    assert body["detail"] == "Internal server error"
    # The client learns nothing about our internals...
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
    # ...but we still record what actually happened.
    assert "hunter2" in caplog.text
