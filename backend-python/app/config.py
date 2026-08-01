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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()