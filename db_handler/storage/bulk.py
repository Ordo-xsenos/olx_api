import asyncio
import asyncpg
import json
import logging
import os
from typing import Dict, List, Optional, Sequence, Type


def _resolve_raw_dsn() -> Optional[str]:
    raw_dsn = os.getenv("RAW_DSN")
    if raw_dsn:
        return raw_dsn
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None
    return database_url.replace("+asyncpg", "")


class BulkWriter:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        dsn = _resolve_raw_dsn()
        if not dsn:
            raise RuntimeError("Не задан RAW_DSN или DATABASE_URL")
        self.pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=5,
            statement_cache_size=0,
        )

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def _with_retries(self, coro_factory) -> None:
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
                await coro_factory()
                return
            except retryable as exc:
                if attempt >= max_attempts:
                    raise
                sleep_for = base_delay * (2 ** (attempt - 1))
                self.logger.warning(
                    "Повтор BulkWriter %s/%s после ошибки: %r",
                    attempt,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(sleep_for)
                attempt += 1

    async def insert_many(self, rows: List[Dict]) -> None:
        if not rows:
            return
        if not self.pool:
            await self.start()
        prepared_rows = [
            (
                r["url"],
                r.get("category"),
                r.get("title"),
                r.get("price"),
                r.get("currency"),
                r.get("location"),
                r.get("precise_location"),
                json.dumps(r.get("parameters") or {}),
                r.get("olx_id"),
            )
            for r in rows
        ]

        async def _run() -> None:
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    WITH updated_by_olx AS (
                        UPDATE products
                        SET
                            url = $1,
                            category = $2,
                            title = $3,
                            price = $4,
                            currency = $5,
                            location = $6,
                            precise_location = $7,
                            parameters = $8::jsonb,
                            olx_id = COALESCE($9::text, products.olx_id)
                        WHERE $9::text IS NOT NULL AND olx_id = $9::text
                        RETURNING id
                    ),
                    updated_by_url AS (
                        UPDATE products
                        SET
                            category = $2,
                            title = $3,
                            price = $4,
                            currency = $5,
                            location = $6,
                            precise_location = $7,
                            parameters = $8::jsonb,
                            olx_id = COALESCE($9::text, products.olx_id)
                        WHERE
                            NOT EXISTS (SELECT 1 FROM updated_by_olx)
                            AND url = $1
                        RETURNING id
                    )
                    INSERT INTO products (
                        url,
                        category,
                        title,
                        price,
                        currency,
                        location,
                        precise_location,
                        parameters,
                        olx_id
                    )
                    SELECT
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7,
                        $8::jsonb,
                        $9::text
                    WHERE
                        NOT EXISTS (SELECT 1 FROM updated_by_olx)
                        AND NOT EXISTS (SELECT 1 FROM updated_by_url)
                    """,
                    prepared_rows,
                )

        await self._with_retries(_run)
        self.logger.info("Синхронизировано %s строк в products", len(rows))
