import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool
import asyncio
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# Загрузка переменных окружения из .env файла
load_dotenv(find_dotenv())
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL")

# Функция create_async_engine ожидает строку подключения с async-драйвером (например, asyncpg)
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0  # <-- ВАЖНО: отключаем кэширование для asyncpg
    }
)

sync_engine = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    echo=False,
    poolclass=NullPool,
)

SessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def db_test_connection() -> str:
    """Тестирует подключение к базе данных и возвращает версию PostgreSQL."""
    async with async_engine.connect() as conn:
        res = await conn.execute(text("SELECT version()"))
        # Метод res.scalar() вернет строку версии
        return res.scalar()

def get_session_maker() -> async_sessionmaker:
    """Ленивая инициализация async_session_maker.
    При первом вызове создаёт engine и session_maker, используя настройки из config.
    """
    global async_engine, SessionLocal
    if SessionLocal is None:
        # импортируем конфиг локально, чтобы не создавать DatabaseSettings при импорте модуля
        database_url = DATABASE_URL
        _engine = create_async_engine(database_url, echo=True)
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return SessionLocal

# Для прямого запуска этого файла оставим тест в блоке __main__
if __name__ == "__main__":
    # Запуск теста в отдельном event loop только при прямом запуске файла
    ver = asyncio.run(db_test_connection())
    print("Версия Postgres:", ver)

