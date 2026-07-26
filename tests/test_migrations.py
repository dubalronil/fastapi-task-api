from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.conftest import MIGRATION_DATABASE_URL

REPO_ROOT = Path(__file__).resolve().parent.parent


def _empty_the_database() -> None:
    # Dropping and recreating the schema is the quickest way to get a Postgres
    # database back to genuinely empty, alembic_version included.
    engine = create_engine(MIGRATION_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def test_migrations_produce_the_schema_in_models():
    # The rest of the suite builds its tables with create_all, straight from
    # models.py, so nothing else here would notice a model change that never
    # made it into a migration. This runs every migration against an empty
    # database and then checks the result matches models.py.
    #
    # Running it on Postgres also proves the migrations work on the engine we
    # deploy to, not just on SQLite.
    _empty_the_database()

    cfg = Config(REPO_ROOT / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", MIGRATION_DATABASE_URL)

    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if models and migrations disagree
