from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://max:max@postgres:5432/maxapp"
    MAX_BOT_TOKEN: SecretStr
    SECRET_KEY: SecretStr
    MAX_INIT_DATA_MAX_AGE: int = 86400
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    PROJECT_NAME: str = "max-miniapp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


ENV = EnvSettings()
