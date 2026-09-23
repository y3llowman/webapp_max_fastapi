from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

class EnvSettings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://max:max@postgres:5432/maxapp"
    MAX_BOT_TOKEN: SecretStr = Field(validation_alias="MAX_TOKEN")
    SECRET_KEY: SecretStr = '91e7aa388ee05ee5bce01c2c3a0ef115d2950b9122cbaa116fa355844b0dca05'
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
