"""Per-client request limits."""

import pytest
from fastapi import Request

from app.rate_limit import client_address, parse_limit


@pytest.mark.parametrize(
    "given,expected",
    [
        ("60/minute", (60, 60)),
        ("10/second", (10, 1)),
        ("1000/hour", (1000, 3600)),
        ("5/minutes", (5, 60)),  # trailing s tolerated
    ],
)
def test_parse_limit(given, expected):
    assert parse_limit(given) == expected


def test_parse_limit_rejects_an_unknown_period():
    with pytest.raises(ValueError):
        parse_limit("5/fortnight")


def _request(headers: dict[str, str], client_host: str | None = "10.0.0.1"):
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 1234) if client_host else None,
    }
    return Request(scope)


def test_client_address_falls_back_to_the_socket_address():
    assert client_address(_request({})) == "10.0.0.1"


def test_client_address_uses_the_forwarded_header():
    # Behind a proxy the socket address is the proxy's, so every visitor would
    # otherwise share one bucket.
    request = _request({"X-Forwarded-For": "203.0.113.5"})
    assert client_address(request) == "203.0.113.5"


def test_client_address_takes_the_rightmost_forwarded_entry():
    # A caller can put anything at the front of this header. The last entry is
    # the one our own proxy observed, so reading the leftmost would let anyone
    # dodge the limit by inventing an address.
    request = _request({"X-Forwarded-For": "1.1.1.1, 203.0.113.5"})
    assert client_address(request) == "203.0.113.5"


# --- behaviour ------------------------------------------------------------


@pytest.fixture
def limited(monkeypatch):
    """Build a throwaway app at a given limit.

    Each case needs its own app: middleware cannot be added once an app has
    started, and every app keeps its own request counters. Building a bare one
    also keeps these tests off the database, since the middleware runs before
    any route does.
    """
    from fastapi import APIRouter, FastAPI
    from fastapi.testclient import TestClient

    from app import rate_limit

    def _build(limit: str) -> TestClient:
        # monkeypatch restores this at teardown — after the requests are made,
        # which matters now the middleware reads the limit per request.
        monkeypatch.setattr(rate_limit.settings, "rate_limit", limit)
        app = FastAPI()

        @app.get("/")
        def health():
            return {"status": "ok"}

        @app.get("/thing")
        def thing():
            return {"ok": True}

        # Mounted the way the real app mounts /tasks. Worth covering: the
        # previous implementation only saw routes declared directly on the
        # app and silently let every included route through unlimited.
        router = APIRouter(prefix="/nested")

        @router.get("")
        def nested():
            return {"ok": True}

        app.include_router(router)

        rate_limit.register_rate_limiting(app)
        return TestClient(app)

    return _build


def test_requests_are_limited_per_client(limited):
    api = limited("3/minute")
    headers = {"X-Forwarded-For": "203.0.113.10"}
    statuses = [api.get("/thing", headers=headers).status_code for _ in range(5)]
    assert statuses == [200, 200, 200, 429, 429]


def test_clients_are_limited_independently(limited):
    api = limited("2/minute")
    for _ in range(3):
        api.get("/thing", headers={"X-Forwarded-For": "203.0.113.20"})

    # A different caller starts with a fresh count.
    other = api.get("/thing", headers={"X-Forwarded-For": "203.0.113.21"})
    assert other.status_code == 200


def test_rate_limited_response_uses_the_standard_error_shape(limited):
    api = limited("1/minute")
    headers = {"X-Forwarded-For": "203.0.113.30"}
    api.get("/thing", headers=headers)
    response = api.get("/thing", headers=headers)

    assert response.status_code == 429
    body = response.json()
    assert {"status", "title", "detail", "request_id"} <= body.keys()
    assert body["status"] == 429
    assert int(response.headers["retry-after"]) > 0


def test_health_check_is_never_limited(limited):
    api = limited("1/minute")
    # A throttled health check would get a healthy instance restarted.
    headers = {"X-Forwarded-For": "203.0.113.40"}
    statuses = [api.get("/", headers=headers).status_code for _ in range(5)]
    assert statuses == [200] * 5


def test_routes_mounted_through_a_router_are_limited(limited):
    # The real app mounts /tasks with include_router. The first attempt at this
    # feature only inspected routes declared directly on the app, so every
    # router route went unlimited while the health check looked protected.
    api = limited("3/minute")
    headers = {"X-Forwarded-For": "203.0.113.50"}
    statuses = [api.get("/nested", headers=headers).status_code for _ in range(5)]
    assert statuses == [200, 200, 200, 429, 429]
