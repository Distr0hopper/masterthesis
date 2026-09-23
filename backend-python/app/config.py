from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_host: str = "localhost"
    database_port: int = 5433
    database_user: str = "moveapps"
    database_password: str = "moveapps"
    database_name: str = "component_repository"

    jwt_secret: str
    jwt_expires_in: int = 86400

    cors_origin: str = "http://localhost:5173"
    port: int = 8000

    environment: str = "local"
    auto_migrate: bool = True

    packaging_executable: str
    github_token: str | None = None

    email_provider: str = "smtp"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from_email: str = "noreply@localhost"

    resend_api_key: str | None = None
    resend_from_email: str | None = None

    otp_expires_in: int = 600
    otp_max_attempts: int = 5
    otp_request_cooldown: int = 60

    # SOS File Format Service - resolves CWL `format` identifiers to labels
    format_service_url: str = "http://localhost:8001/api/v1"
    format_service_timeout: float = 30.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()