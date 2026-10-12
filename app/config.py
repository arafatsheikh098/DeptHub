from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production"
    DATABASE_URL: str = "sqlite:///./depthub.db"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    TIMEZONE: str = "Asia/Dhaka"
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    TERM_START: str = "2026-01-01"
    TERM_END: str = "2026-06-30"
    FORWARDED_ALLOW_IPS: str = "*"

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.ENV == "production" and (
            not self.SECRET_KEY
            or self.SECRET_KEY == "insecure-dev-secret-key-change-in-production"
            or "insecure" in self.SECRET_KEY
        ):
            msg = "Production refuses to start with default or insecure SECRET_KEY"
            raise ValueError(msg)
        return self


settings = Settings()
