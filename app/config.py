from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Microservicio de Usuarios"
    database_url: str | None = None
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 3
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    internal_service_credentials: str = "{}"
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()


def validate_settings(candidate: Settings | None = None) -> None:
    configured = candidate or settings
    missing = []
    if not configured.database_url:
        missing.append("DATABASE_URL")
    if not configured.jwt_secret_key:
        missing.append("JWT_SECRET_KEY")
    if not configured.internal_service_credentials or configured.internal_service_credentials == "{}":
        missing.append("INTERNAL_SERVICE_CREDENTIALS")
    if missing:
        raise RuntimeError(f"Variables de entorno criticas no configuradas: {', '.join(missing)}")
    if configured.app_env.lower() == "production" and configured.database_url.startswith("sqlite"):
        raise RuntimeError("SQLite no esta permitido en produccion")
    if configured.app_env.lower() == "production" and configured.jwt_secret_key == "change-this-secret-key":
        raise RuntimeError("JWT_SECRET_KEY debe ser reemplazado en produccion")
    if configured.app_env.lower() == "production" and "*" in configured.cors_origins_list:
        raise RuntimeError("CORS_ORIGINS no puede usar comodines en produccion")
