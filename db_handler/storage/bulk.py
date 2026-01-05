import asyncpg

class BulkWriter:
    def __init__(self, dsn: str):
        self.dsn = dsn

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)

    async def insert_many(self, rows: list[dict]):
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO real_estates(title, price_value, currency, location, raw, url)
                VALUES($1,$2,$3,$4,$5,$6)
                ON CONFLICT (url) DO NOTHING
            """, [
                (
                    r["title"], r["price_value"], r["currency"],
                    r["location"], r, r["url"]
                ) for r in rows
            ])
