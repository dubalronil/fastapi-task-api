from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./tasks.db"

    # Real environment variables win over .env, which wins over the default above.
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
