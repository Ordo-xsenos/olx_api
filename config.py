from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""

    # База данных
    database_url: str = Field(alias="DATABASE_URL")

    # Telegram
    telegram_bot_token: str = Field(alias="TOKEN")
    admins: str = Field(default="", alias="ADMINS")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Парсинг
    schedule_category_id: Optional[str] = Field(default=None, alias="SCHEDULE_CATEGORY_ID")
    schedule_category_name: Optional[str] = Field(default=None, alias="SCHEDULE_CATEGORY_NAME")
    parse_schedule_time: Optional[str] = Field(default=None, alias="PARSE_SCHEDULE_TIME")
    cleanup_missing: str = Field(default="0", alias="CLEANUP_MISSING")
    max_concurrent_requests: int = Field(default=5, alias="MAX_CONCURRENT_REQUESTS")
    batch_size: int = Field(default=200, alias="BATCH_SIZE")

    # Webhook
    webhook_url: Optional[str] = Field(default=None, alias="WEBHOOK_URL")
    webhook_timeout_seconds: float = Field(default=10.0, alias="WEBHOOK_TIMEOUT_SECONDS")

    # Retry настройки
    db_max_retries: int = Field(default=3, alias="DB_MAX_RETRIES")
    db_retry_delay: float = Field(default=0.5, alias="DB_RETRY_DELAY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,  # Позволяет использовать как alias, так и имя поля
        extra="ignore",  # Игнорировать дополнительные поля из .env
    )


# Глобальный экземпляр настроек
settings = Settings()
