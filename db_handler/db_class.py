import asyncio
import asyncpg
import logging
import os
from typing import Optional, List, Dict, Any, Sequence, Type

# Логирование
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)


class PostgresHandler:
    """Класс для работы с PostgreSQL через asyncpg."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None,
        dsn: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def _with_retries(self, coro_factory):
        max_attempts = int(os.getenv("DB_MAX_RETRIES", "3"))
        base_delay = float(os.getenv("DB_RETRY_DELAY", "0.5"))
        retryable: Sequence[Type[BaseException]] = (
            asyncpg.PostgresError,
            ConnectionError,
            OSError,
            TimeoutError,
        )
        attempt = 1
        while True:
            try:
                return await coro_factory()
            except retryable as exc:
                if attempt >= max_attempts:
                    raise
                sleep_for = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Повтор запроса к БД %s/%s после ошибки: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(sleep_for)
                attempt += 1

    async def create_pool(self, min_size: int = 5, max_size: int = 20) -> None:
        """Создание пула соединений с базой данных."""
        try:
            async def _create() -> None:
                if self.dsn:
                    self.pool = await asyncpg.create_pool(
                        dsn=self.dsn,
                        min_size=min_size,
                        max_size=max_size,
                        statement_cache_size=0,
                    )
                else:
                    self.pool = await asyncpg.create_pool(
                        host=self.host,
                        port=self.port,
                        user=self.user,
                        password=self.password,
                        database=self.database,
                        min_size=min_size,
                        max_size=max_size,
                        statement_cache_size=0,
                    )

            await self._with_retries(_create)
            logger.info("Пул соединений успешно создан")
        except Exception as e:
            logger.error(f"Ошибка создания пула соединений: {e}")
            raise

    async def close_pool(self) -> None:
        """Закрытие пула соединений."""
        if self.pool:
            await self.pool.close()
            logger.info("Пул соединений закрыт")

    async def init_database(self) -> None:
        """Инициализация таблиц базы данных."""
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            tg_id BIGINT UNIQUE,
            username TEXT UNIQUE,
            is_admin BOOLEAN NOT NULL DEFAULT FALSE,
            is_banned BOOLEAN NOT NULL DEFAULT FALSE,
            ban_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_users_table)
                await conn.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason TEXT"
                )
                await conn.execute(
                    "UPDATE users SET username = regexp_replace(username, '^@', '') WHERE username LIKE '@%'"
                )
            logger.info("Таблица users готова.")
        except Exception as e:
            logger.error(f"Ошибка инициализации таблицы users: {e}")

        create_settings_table = """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_settings_table)
                await conn.execute(
                    """
                    INSERT INTO settings (key, value)
                    VALUES ('allow_non_admins', '1')
                    ON CONFLICT (key) DO NOTHING
                    """
                )
            logger.info("Таблица settings готова.")
        except Exception as e:
            logger.error(f"Ошибка инициализации таблицы settings: {e}")

        try:
            async with self.pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT to_regclass('public.products')"
                )
            if exists:
                logger.info("Таблица products найдена.")
            else:
                logger.error("Таблица products не найдена. Запусти миграции Alembic.")
        except Exception as e:
            logger.error(f"Ошибка проверки таблицы products: {e}")
        return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_users_table)
                logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

    async def execute_query(self, query: str, *params) -> Any:
        """Выполнение произвольного SQL запроса."""
        try:
            async def _run():
                async with self.pool.acquire() as conn:
                    return await conn.execute(query, *params)

            return await self._with_retries(_run)
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"SQL-запрос: {query}")
            return None

    async def fetch_query(self, query: str, *params) -> List[Dict[str, Any]]:
        """Выполнение SELECT запроса."""
        try:
            async def _run():
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    return [dict(row) for row in rows]

            return await self._with_retries(_run)
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса: {e}")
            logger.error(f"SQL-запрос: {query}")
            return []

    async def fetchrow_query(
        self, query: str, *params
    ) -> Optional[Dict[str, Any]]:
        """Выполнение SELECT запроса с получением одной строки."""
        try:
            async def _run():
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(query, *params)
                    return dict(row) if row else None

            return await self._with_retries(_run)
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса: {e}")
            logger.error(f"SQL-запрос: {query}")
            return None
