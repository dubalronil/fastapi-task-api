"""Request ids, the access log, and the two output formats."""

import json
import logging

from app.logging_config import JsonFormatter, TextFormatter, request_id


def test_response_carries_a_request_id_header(client):
    response = client.get("/tasks")
    assert response.headers["x-request-id"]


def test_incoming_request_id_is_reused(client):
    # A proxy or another service usually sets this. Keeping it means one id
    # follows a request across every service that touched it.
    response = client.get("/tasks", headers={"X-Request-ID": "from-the-proxy"})
    assert response.headers["x-request-id"] == "from-the-proxy"


def test_overlong_request_id_is_replaced(client):
    # The header is client-controlled and lands on every log line for the
    # request, so an unbounded value would let a caller pad the logs.
    response = client.get("/tasks", headers={"X-Request-ID": "x" * 5000})
    returned = response.headers["x-request-id"]
    assert returned != "x" * 5000
    assert len(returned) <= 64


def test_each_request_gets_a_distinct_id(client):
    first = client.get("/tasks").headers["x-request-id"]
    second = client.get("/tasks").headers["x-request-id"]
    assert first != second


def test_error_response_id_matches_the_header(client):
    # This is what makes an error report actionable: the user quotes the id,
    # and it is on every log line for that request.
    response = client.get("/tasks/999")
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_access_log_records_method_path_status_and_duration(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/tasks/999")

    record = next(r for r in caplog.records if r.name == "app.access")
    assert record.method == "GET"
    assert record.path == "/tasks/999"
    assert record.status == 404
    assert isinstance(record.duration_ms, float)


def _record(**extra):
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello", (), None)
    record.__dict__.update(extra)
    return record


def test_json_formatter_emits_one_parsable_object():
    token = request_id.set("abc123")
    try:
        line = JsonFormatter().format(_record(status=200))
    finally:
        request_id.reset(token)

    payload = json.loads(line)
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "abc123"
    assert payload["status"] == 200  # extra={} fields survive


def test_text_formatter_appends_extras():
    line = TextFormatter("%(message)s").format(_record(status=200, path="/tasks"))
    assert line.startswith("hello")
    assert "status=200" in line
    assert "path=/tasks" in line


def test_request_id_defaults_outside_a_request():
    # Startup and shutdown logs have no request to belong to.
    assert request_id.get() == "-"
