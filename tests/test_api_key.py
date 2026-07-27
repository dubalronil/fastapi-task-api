"""Writes require the API key; reads do not."""

import pytest

from app import security

KEY = "test-secret-key"
NEW_TASK = {"title": "needs a key"}
FULL_TASK = {"title": "needs a key", "description": None, "completed": False}


@pytest.fixture
def protected(monkeypatch):
    """Turn the key requirement on for a test."""
    monkeypatch.setattr(security.settings, "api_key", KEY)


def test_reads_stay_public(client, protected):
    # The API is still browsable, which is the point of gating only writes.
    assert client.get("/tasks").status_code == 200
    assert client.get("/tasks/999999").status_code == 404


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/tasks", NEW_TASK),
        ("put", "/tasks/1", FULL_TASK),
        ("patch", "/tasks/1", {"completed": True}),
        ("delete", "/tasks/1", None),
    ],
)
def test_writes_are_rejected_without_a_key(client, protected, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


def test_every_write_endpoint_requires_the_key(client):
    """Structural check, so a new endpoint cannot be added unprotected.

    The parametrised test above only covers the routes listed in it. This reads
    the OpenAPI schema instead, so any future write endpoint is included
    automatically. Written after PUT and PATCH were briefly left unguarded.
    """
    spec = client.get("/openapi.json").json()
    write_methods = {"post", "put", "patch", "delete"}

    unprotected = [
        f"{method.upper()} {path}"
        for path, operations in spec["paths"].items()
        for method, operation in operations.items()
        if method in write_methods and not operation.get("security")
    ]
    assert unprotected == []


def test_reads_are_not_gated(client):
    # Gating reads would stop the API being browsable, which is the whole
    # reason only writes are protected.
    spec = client.get("/openapi.json").json()
    gated_reads = [
        path
        for path, operations in spec["paths"].items()
        if operations.get("get", {}).get("security")
    ]
    assert gated_reads == []


def test_a_wrong_key_is_rejected(client, protected):
    response = client.post("/tasks", json=NEW_TASK, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_the_right_key_is_accepted(client, protected):
    response = client.post("/tasks", json=NEW_TASK, headers={"X-API-Key": KEY})
    assert response.status_code == 201


def test_rejection_uses_the_standard_error_shape(client, protected):
    response = client.post("/tasks", json=NEW_TASK)
    body = response.json()
    assert {"status", "title", "detail", "request_id"} <= body.keys()
    assert body["status"] == 401
    assert body["detail"] == "Invalid or missing API key"
    # A 401 without this header tells the caller nothing about how to proceed.
    assert response.headers["www-authenticate"] == "ApiKey"


def test_writes_are_open_when_no_key_is_configured(client, monkeypatch):
    # Keeps local development and the test suite usable. Deployments set the
    # key; warn_if_unprotected() logs at startup when they have not.
    monkeypatch.setattr(security.settings, "api_key", None)
    assert client.post("/tasks", json=NEW_TASK).status_code == 201


def test_startup_warns_when_unprotected(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(security.settings, "api_key", None)
    with caplog.at_level(logging.WARNING):
        security.warn_if_unprotected()
    assert "open to anyone" in caplog.text


def test_no_warning_when_protected(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(security.settings, "api_key", KEY)
    with caplog.at_level(logging.WARNING):
        security.warn_if_unprotected()
    assert caplog.text == ""
