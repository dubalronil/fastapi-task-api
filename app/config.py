from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./tasks.db"

    log_level: str = "INFO"
    # Plain text by default so local logs stay readable. Turn on in production,
    # where a log collector has to parse them.
    log_json: bool = False

    # Real environment variables win over .env, which wins over the default above.
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
