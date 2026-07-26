from pathlib import Path

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_migrations_produce_the_schema_in_models(tmp_path):
    # The rest of the suite builds its tables with create_all, straight from
    # models.py, so nothing else here would notice a model change that never
    # made it into a migration. This runs every migration against an empty
    # database and then checks the result matches models.py.
    cfg = Config(REPO_ROOT / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migrations.db'}")

    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if models and migrations disagree
