from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import get_database_settings
import asyncio

# Лениво получаем настройки
_settings = get_database_settings()
DATABASE_URL = _settings.database_url

# create_async_engine ожидает строку подключения с async драйвером (например, asyncpg)
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def db_test_connection() -> str:
    """Тестирует подключение к базе данных и возвращает версию PostgreSQL."""
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT version()"))
        # res.scalar() даст строку версии
        return res.scalar()

def get_session_maker() -> async_sessionmaker:
    """Ленивая инициализация async_session_maker.
    При первом вызове создаёт engine и session_maker, используя настройки из config.
    """
    global _engine, _SessionLocal
    if _SessionLocal is None:
        # импортируем конфиг локально, чтобы не создавать DatabaseSettings при импорте модуля
        from config import get_database_settings
        settings = get_database_settings()
        database_url = settings.database_url
        _engine = create_async_engine(database_url, echo=True)
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return _SessionLocal

# Для прямого запуска этого файла оставим тест в блоке __main__
if __name__ == '__main__':
    # Запуск теста в отдельном event loop только при прямом запуске файла
    ver = asyncio.run(db_test_connection())
    print('Postgres version:', ver)
