"""The health check has to fail when the app cannot actually serve requests."""

from sqlalchemy.exc import OperationalError


def test_health_check_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_reports_503_when_the_database_is_unreachable(
    client, db_session, monkeypatch
):
    # A check that only proves the process is alive would return 200 here, and
    # a platform would keep routing traffic to an instance that 500s on every
    # real request.
    def unreachable(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(db_session, "execute", unreachable)

    response = client.get("/")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
