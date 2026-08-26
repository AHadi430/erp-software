from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Paint Shop ERP"
    environment: str = "development"
    secret_key: str
    access_token_expire_minutes: int = 480
    database_url: str
    cors_origins: str = "http://localhost:5173"
    initial_admin_email: str = "admin@paintshop.local"
    initial_admin_password: str = "ChangeMe123!"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
