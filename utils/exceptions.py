import asyncpg
import httpx
from typing import Type


# Исключения которые можно ретраить
RETRYABLE_EXCEPTIONS = (
    asyncpg.PostgresError,
    httpx.HTTPError,
    ConnectionError,
    OSError,
    TimeoutError,
)

# Системные исключения которые нельзя глушить
SYSTEM_EXCEPTIONS = (
    KeyboardInterrupt,
    SystemExit,
    GeneratorExit,
)


def is_retryable(exc: Exception) -> bool:
    """Проверяет можно ли ретраить исключение."""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def should_reraise(exc: Exception) -> bool:
    """Проверяет нужно ли пробросить исключение дальше."""
    return isinstance(exc, SYSTEM_EXCEPTIONS)
