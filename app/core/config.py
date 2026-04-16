from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NRI Plot Sentinel API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-to-a-32-byte-secret-key-now"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7
    device_provisioning_token_expire_minutes: int = 60 * 24 * 30
    device_session_token_expire_minutes: int = 60 * 8
    database_url: str = "sqlite:///./data/nri_plot_sentinel.db"
    default_owner_email: str = "owner@example.com"
    default_owner_password: str = "ChangeMe123!"
    default_ops_admin_email: str = "ops@example.com"
    default_ops_admin_password: str = "ChangeMe123!"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("database_url")
    @classmethod
    def normalize_sqlite_path(cls, value: str) -> str:
        if value.startswith("sqlite://") and not value.startswith("sqlite:///"):
            return value.replace("sqlite://", "sqlite:///")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
