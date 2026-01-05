import asyncpg
from typing import Optional, List, Dict, Any
import logging

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(ch)

DEFAULT_FACULTIES = ["Gryffindor", "Hufflepuff", "Ravenclaw", "Slytherin"]


class PostgresHandler:
    """Класс для работы с PostgreSQL базой данных через asyncpg"""

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

    async def create_pool(self, min_size: int = 5, max_size: int = 20) -> None:
        """Создание пула соединений с базой данных"""
        try:
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
            logger.info("Пул соединений успешно создан")
        except Exception as e:
            logger.error(f"Ошибка создания пула соединений: {e}")
            raise

    async def close_pool(self) -> None:
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Пул соединений закрыт")

    async def init_database(self) -> None:
        """Инициализация таблиц базы данных"""
        create_users_table = """"""

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_users_table)

                logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

    # Общие методы
    async def execute_query(self, query: str, *params) -> Any:
        """Выполнение произвольного SQL запроса"""
        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *params)
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            return None

    async def fetch_query(self, query: str, *params) -> List[Dict[str, Any]]:
        """Выполнение SELECT запроса"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса: {e}")
            return []

    async def fetchrow_query(
        self, query: str, *params
    ) -> Optional[Dict[str, Any]]:
        """Выполнение SELECT запроса с получением одной строки"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса: {e}")
            return None

