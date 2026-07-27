from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Matches docker-compose.yml, so `docker compose up -d` is enough to run
    # the app without writing a .env at all.
    database_url: str = "postgresql+psycopg://tasks:tasks@localhost:5432/tasks"

    log_level: str = "INFO"
    # Plain text by default so local logs stay readable. Turn on in production,
    # where a log collector has to parse them.
    log_json: bool = False

    # Real environment variables win over .env, which wins over the default above.
    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        # Hosting providers hand out "postgres://" or "postgresql://".
        # SQLAlchemy maps the first to no dialect at all and the second to
        # psycopg2, which we do not install, so the app would fail on boot
        # against a provider-supplied URL. Normalising here lets the deploy use
        # DATABASE_URL exactly as given.
        if url.startswith("postgres://"):
            url = f"postgresql://{url.removeprefix('postgres://')}"
        if url.startswith("postgresql://"):
            url = f"postgresql+psycopg://{url.removeprefix('postgresql://')}"
        return url


settings = Settings()
