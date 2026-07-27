from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # Matches docker-compose.yml, so `docker compose up -d` is enough to run
    # the app without writing a .env at all.
    database_url: str = "postgresql+psycopg://tasks:tasks@localhost:5432/tasks"

    log_level: str = "INFO"
    # Plain text by default so local logs stay readable. Turn on in production,
    # where a log collector has to parse them.
    log_json: bool = False

    # Browser origins allowed to call this API. The default covers a Next.js
    # dev server; the deployed frontend's origin is added per environment.
    #
    # NoDecode turns off the JSON parsing pydantic-settings applies to list
    # fields from the environment. Without it a comma-separated value fails
    # before the validator below ever runs.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Real environment variables win over .env, which wins over the default above.
    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        # Accept a comma-separated string so the value can be typed into a
        # hosting dashboard, rather than requiring JSON for a list field.
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

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
