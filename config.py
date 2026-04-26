from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""

    # База данных
    database_url: str

    # Telegram
    telegram_bot_token: str
    admins: str = ""
    telegram_chat_id: Optional[str] = None

    # Парсинг
    schedule_category_id: Optional[str] = None
    schedule_category_name: Optional[str] = None
    parse_schedule_time: Optional[str] = None
    cleanup_missing: str = "0"
    max_concurrent_requests: int = 5
    batch_size: int = 200

    # Webhook
    webhook_url: Optional[str] = None
    webhook_timeout_seconds: float = 10.0

    # Retry настройки
    db_max_retries: int = 3
    db_retry_delay: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Глобальный экземпляр настроек
settings = Settings()
