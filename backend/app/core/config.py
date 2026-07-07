from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Telemetry
    POSTHOG_API_KEY: str | None = None
    POSTHOG_HOST: str = "https://us.i.posthog.com"
    SENTRY_DSN: str | None = None

    APP_ENV: str = "development"
    SECRET_KEY: str
    INTERNAL_API_KEY: str
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Encryption
    FERNET_KEY: str

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Sync settings
    SYNC_POLL_INTERVAL: int = 300
    SYNC_BATCH_SIZE: int = 50

    # Outlook Webhooks Canary Flag
    OUTLOOK_WEBHOOKS_ENABLED: bool = False

    # SMTP Forwarding Settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_ADDRESS: str = ""

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [self.FRONTEND_URL, "http://localhost:3000"]


settings = Settings()
