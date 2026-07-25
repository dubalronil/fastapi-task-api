from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Each attribute is a config value. The default here is used when the
    # value isn't found in the environment or the .env file.
    database_url: str = "sqlite:///./tasks.db"

    # Tell pydantic-settings to load values from a file named .env
    model_config = SettingsConfigDict(env_file=".env")


# One shared instance the rest of the app imports.
settings = Settings()
