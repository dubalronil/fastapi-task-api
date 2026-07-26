from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401 — imported so its table registers on Base
from app.config import settings
from app.database import Base

config = context.config

# Take the database URL from our own settings rather than alembic.ini, so there
# is one source of truth and no connection string in a committed file. A caller
# that already set a URL (the migration test) keeps its own.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# What autogenerate compares the database against.
target_metadata = Base.metadata

# SQLite can't ALTER most things in place, so Alembic has to copy the table,
# change it, and swap it back. Read back from config rather than settings, since
# a caller may have supplied a different URL above.
BATCH = config.get_main_option("sqlalchemy.url").startswith("sqlite")


def run_migrations_offline() -> None:
    # Emits SQL to stdout instead of running it, for `alembic upgrade --sql`.
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=BATCH,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=BATCH,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
