"""DATABASE_URL has to work in the shape a hosting provider supplies it."""

import pytest

from app.config import Settings

PROVIDER_URL = "postgres://u:p@host:5432/railway"
EXPECTED = "postgresql+psycopg://u:p@host:5432/railway"


@pytest.mark.parametrize(
    "given,expected",
    [
        # Railway and Render hand out this form; SQLAlchemy would pick psycopg2.
        ("postgresql://u:p@host:5432/railway", EXPECTED),
        # Heroku's older form; SQLAlchemy rejects it outright.
        (PROVIDER_URL, EXPECTED),
        # Already explicit — left alone.
        (EXPECTED, EXPECTED),
        # Not Postgres — left alone.
        ("sqlite:///./tasks.db", "sqlite:///./tasks.db"),
    ],
)
def test_database_url_is_normalised_to_psycopg(given, expected):
    assert Settings(database_url=given).database_url == expected


def test_normalised_url_actually_builds_an_engine():
    # The point of the normalisation: a provider-supplied URL has to produce a
    # working engine, not just a tidier string.
    from sqlalchemy import create_engine

    engine = create_engine(Settings(database_url=PROVIDER_URL).database_url)
    assert engine.dialect.driver == "psycopg"
