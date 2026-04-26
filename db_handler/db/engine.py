from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from config import settings

# Функция create_async_engine ожидает строку подключения с async-драйвером (например, asyncpg)
async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0  # <-- ВАЖНО: отключаем кэширование для asyncpg
    }
)

sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", ""),
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
        return res.scalar()

def get_session_maker() -> async_sessionmaker:
    """Возвращает async_session_maker."""
    return SessionLocal

if __name__ == "__main__":
    import asyncio
    ver = asyncio.run(db_test_connection())
    print("Версия Postgres:", ver)

