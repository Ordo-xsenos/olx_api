# storage/bulk.py
import asyncpg
import os
import json
from typing import List, Dict

RAW_DSN = os.getenv("RAW_DSN")  # без +asyncpg

class BulkWriter:
    def __init__(self):
        self.pool = None

    async def start(self):
        self.pool = await asyncpg.create_pool(
            dsn=RAW_DSN,
            min_size=1,
            max_size=5,
            statement_cache_size=0,  # ОБЯЗАТЕЛЬНО
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_many(self, rows: List[Dict]):
        if not self.pool:
            await self.start()
        async with self.pool.acquire() as conn:
            # пример executemany с ON CONFLICT
            await conn.executemany(
                """
                INSERT INTO real_estates (url, title, price_value, currency, 
                            location, precise_location, parameters, olx_id)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (url) DO UPDATE
                SET title = EXCLUDED.title,
                    price_value = EXCLUDED.price_value,
                    currency = EXCLUDED.currency,
                    parameters = EXCLUDED.parameters,
                    precise_location = EXCLUDED.precise_location,
                    location = EXCLUDED.location
                """,
                [
                    (
                        r["url"],
                        r.get("title"),
                        r.get("price_value"),
                        r.get("currency"),
                        r.get("location"),
                        r.get("precise_location"),
                        json.dumps(r.get("parameters", {})),
                        r.get("olx_id"),
                    )
                    for r in rows
                ],
            )
