from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://attendance:attendance@localhost:5432/attendance"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    # Mobile sessions must survive for a long time: the Android app keeps the token in DataStore
    # and should never ask for the password again unless it is revoked (password change/reset or
    # deactivation). Ten years is effectively "until revoked".
    access_token_minutes: int = 60 * 24 * 365 * 10

    # Used to decide which calendar day a check-in belongs to.
    timezone: str = "Asia/Tehran"

    # Reject GPS fixes less accurate than this (meters).
    max_gps_accuracy_m: float = 100.0

    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # Created on first startup if no admin exists yet.
    admin_bootstrap_username: str = "admin"
    admin_bootstrap_password: str | None = None

    cors_origins: list[str] = []

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()


def validate_settings(s: Settings) -> None:
    if s.is_production and (len(s.jwt_secret) < 32 or s.jwt_secret == "change-me-in-production"):
        raise RuntimeError("JWT_SECRET must be set to a strong value (32+ chars) in production")
