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
            raise RuntimeError("RAW_DSN or DATABASE_URL is not set")
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
                    "BulkWriter retry %s/%s after error: %s",
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
        async def _run() -> None:
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
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
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)
                    ON CONFLICT (url) DO UPDATE
                    SET category = EXCLUDED.category,
                        title = EXCLUDED.title,
                        price = EXCLUDED.price,
                        currency = EXCLUDED.currency,
                        location = EXCLUDED.location,
                        precise_location = EXCLUDED.precise_location,
                        parameters = EXCLUDED.parameters,
                        olx_id = EXCLUDED.olx_id
                    """,
                    [
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
                    ],
                )

        await self._with_retries(_run)
        self.logger.info("Upserted %s rows into products", len(rows))
