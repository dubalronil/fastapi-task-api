"""CORS, which is what lets a browser frontend call this API at all."""

ALLOWED = "http://localhost:3000"
# .example is reserved by RFC 2606 and can never be registered, so a
# placeholder here can never collide with a real site.
BLOCKED = "https://untrusted.example"


def test_preflight_is_allowed_for_a_known_origin(client):
    # The browser sends this OPTIONS request by itself before a PATCH, and
    # refuses to send the real one unless the answer approves it.
    response = client.options(
        "/tasks/1",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_actual_request_carries_the_allow_origin_header(client):
    response = client.get("/tasks", headers={"Origin": ALLOWED})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_request_id_is_readable_by_the_browser(client):
    # Scripts can only read a handful of response headers unless the server
    # names the others. Without expose_headers the frontend would receive
    # X-Request-ID and still be unable to read it.
    response = client.get("/tasks", headers={"Origin": ALLOWED})
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]


def test_unknown_origin_is_not_approved(client):
    response = client.get("/tasks", headers={"Origin": BLOCKED})
    # The request still succeeds — CORS is enforced by the browser, not here —
    # but without this header the browser refuses to hand the body to the page.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_error_responses_are_also_readable_by_the_browser(client):
    # A 404 without the header shows up in the browser as an opaque network
    # failure, which hides the real status from the frontend.
    response = client.get("/tasks/999999", headers={"Origin": ALLOWED})
    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == ALLOWED
