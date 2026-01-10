import asyncpg
from typing import Iterable, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BulkWriter:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=1,
            max_size=10,
            statement_cache_size=0
        )
        logger.info("BulkWriter pool connected")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_real_estates(self, rows: Iterable[Dict[str, Any]]):
        if not self.pool:
            raise RuntimeError("BulkWriter not connected")

        async with self.pool.acquire() as conn:
            await conn.copy_records_to_table(
                "real_estates",
                records=[
                    (
                        r["title"],
                        r["created_at"],
                        r["price_value"],
                        r["currency"],
                        r["location"],
                        r["precise_location"],
                        r["parameters"],
                        r["olx_id"],
                        r["url"],
                    )
                    for r in rows
                ],
                columns=[
                    "title",
					"created_at",
                    "price_value",
                    "currency",
                    "location",
                    "precise_location",
                    "parameters",
                    "olx_id",
                    "url",
                ],
            )
