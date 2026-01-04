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
        create_users_table = """
                             CREATE TABLE IF NOT EXISTS users \
                             ( \
                                 user_id \
                                 BIGINT \
                                 PRIMARY \
                                 KEY, \
                                 username \
                                 VARCHAR \
                             ( \
                                 255 \
                             ),
                                 first_name VARCHAR \
                             ( \
                                 255 \
                             ),
                                 last_name VARCHAR \
                             ( \
                                 255 \
                             ),
                                 is_bot BOOLEAN DEFAULT FALSE,
                                 language_code VARCHAR \
                             ( \
                                 10 \
                             ),
                                 faculty VARCHAR(255) NOT NULL,
                                 rating INTEGER DEFAULT 1 CHECK (rating > 0),
                                 created_at TIMESTAMP DEFAULT 
                                                    CURRENT_TIMESTAMP,
                                 updated_at TIMESTAMP DEFAULT 
                                                    CURRENT_TIMESTAMP
                                 ); \
                             """
        # language=postgresql
        create_messages_table = """
                                CREATE TABLE IF NOT EXISTS messages \
                                ( \
                                    id \
                                    SERIAL \
                                    PRIMARY \
                                    KEY, \
                                    user_id \
                                    BIGINT \
                                    REFERENCES \
                                    users \
                                ( \
                                    user_id \
                                ),
                                    message_id BIGINT,
                                    text TEXT,
                                    message_type VARCHAR \
                                ( \
                                    50 \
                                ),
                                    created_at TIMESTAMP DEFAULT 
                                                             CURRENT_TIMESTAMP
                                    ); \
                                """

        create_user_states_table = """
                                   CREATE TABLE IF NOT EXISTS user_states \
                                   ( \
                                       user_id \
                                       BIGINT \
                                       PRIMARY \
                                       KEY \
                                       REFERENCES \
                                       users \
                                   ( \
                                       user_id \
                                   ),
                                       state VARCHAR \
                                   ( \
                                       255 \
                                   ),
                                       data JSONB,
                                       updated_at TIMESTAMP DEFAULT 
                                                                CURRENT_TIMESTAMP
                                       ); \
                                   """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_users_table)
                await conn.execute(create_messages_table)
                await conn.execute(create_user_states_table)

                logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

    async def add_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_bot: bool = False,
        language_code: Optional[str] = None,
        faculty: Optional[str] = None,
        rating: int = 1,
    ) -> bool:
        """Добавляет пользователя или обновляет его.
        Если faculty не указан — выберет автоматически.
        Защита от гонок реализована: мы начинаем транзакцию
                                            и внутри вызываем assign_faculty,
        затем вставляем/обновляем запись.
        """
        if rating <= 0:
            rating = 1

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    if faculty is None:
                        # выбрать факультет безопасно внутри транзакции
                        faculty = await self.assign_faculty(conn)

                    # Используем UPSERT (ON CONFLICT)
                    #               для атомарного вставки/обновления
                    insert_q = """
                               INSERT INTO users (user_id, username, is_bot, 
                                    language_code, created_at, updated_at)
                               VALUES ($1, $2, $3, $4, 
                                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                               ON CONFLICT (user_id) DO UPDATE SET
                               username = EXCLUDED.username,
                               first_name = EXCLUDED.first_name,
                               last_name = EXCLUDED.last_name,
                               is_bot = EXCLUDED.is_bot,
                               language_code = EXCLUDED.language_code,
                               faculty = EXCLUDED.faculty,
                               rating = EXCLUDED.rating,
                               updated_at = CURRENT_TIMESTAMP; \
                               """
                    await conn.execute(
                        insert_q,
                        user_id,
                        username,
                        first_name,
                        last_name,
                        is_bot,
                        language_code,
                        faculty,
                        rating,
                    )
                    logger.info(
                        f"User {user_id} added/updated with faculty={faculty}"
                    )
            return True
        except Exception as e:
            logger.exception(
                f"Error while adding/updating user {user_id}: {e}"
            )
            return False

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        query = "SELECT * FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, user_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей: {e}")
            return []

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        query = "DELETE FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, user_id)
                return "DELETE 1" in result
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
            return False

    # Методы для работы с сообщениями
    async def add_message(
        self,
        user_id: int,
        message_id: int,
        text: str = None,
        message_type: str = "text",
    ) -> bool:
        """Добавление сообщения"""
        query = """
                INSERT INTO messages (user_id, message_id, text, message_type)
                VALUES ($1, $2, $3, $4) \
                """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query, user_id, message_id, text, message_type
                )
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления сообщения: {e}")
            return False

    async def get_user_messages(
        self, user_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получение сообщений пользователя"""
        query = """
                SELECT * \
                FROM messages
                WHERE user_id = $1
                ORDER BY created_at DESC
                    LIMIT $2 \
                """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(
                f"Ошибка получения сообщений пользователя {user_id}: {e}"
            )
            return []

    async def get_messages_count(self, user_id: int = None) -> int:
        """Подсчет количества сообщений"""
        if user_id:
            query = "SELECT COUNT(*) FROM messages WHERE user_id = $1"
            params = [user_id]
        else:
            query = "SELECT COUNT(*) FROM messages"
            params = []

        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(query, *params)
                return count or 0
        except Exception as e:
            logger.error(f"Ошибка подсчета сообщений: {e}")
            return 0

    # Методы для работы с состояниями пользователей
    async def set_user_state(
        self, user_id: int, state: str, data: Dict[str, Any] = None
    ) -> bool:
        """Установка состояния пользователя"""
        query = """
                INSERT INTO user_states (user_id, state, data, updated_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP) 
                ON CONFLICT (user_id) DO \
                UPDATE SET
                    state = EXCLUDED.state, \
                    data = EXCLUDED.data, \
                    updated_at = CURRENT_TIMESTAMP \
                """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, user_id, state, data)
                return True
        except Exception as e:
            logger.error(
                f"Ошибка установки состояния пользователя {user_id}: {e}"
            )
            return False

    async def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение состояния пользователя"""
        query = "SELECT * FROM user_states WHERE user_id = $1"
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, user_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(
                f"Ошибка получения состояния пользователя {user_id}: {e}"
            )
            return None

    async def clear_user_state(self, user_id: int) -> bool:
        """Очистка состояния пользователя"""
        query = "DELETE FROM user_states WHERE user_id = $1"
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, user_id)
                return "DELETE" in result
        except Exception as e:
            logger.error(
                f"Ошибка очистки состояния пользователя {user_id}: {e}"
            )
            return False

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

    # Статистические методы
    async def get_users_count(self) -> int:
        """Получение количества пользователей"""
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM users")
                return count or 0
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0

    async def get_stats(self) -> Dict[str, int]:
        """Получение общей статистики"""
        try:
            async with self.pool.acquire() as conn:
                users_count = (
                    await conn.fetchval("SELECT COUNT(*) FROM users") or 0
                )
                messages_count = (
                    await conn.fetchval("SELECT COUNT(*) FROM messages") or 0
                )
                active_states = (
                    await conn.fetchval("SELECT COUNT(*) FROM user_states")
                    or 0
                )

                return {
                    "users": users_count,
                    "messages": messages_count,
                    "active_states": active_states,
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"users": 0, "messages": 0, "active_states": 0}
