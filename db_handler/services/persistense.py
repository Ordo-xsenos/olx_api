from sqlalchemy.util import await_fallback
from db_handler.storage.bulk import BulkWriter

DSN = "postgresql://postgres.mynwlkaflcwccymqnuek:Ordo_xsenos2010@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1"
bulk = await_fallback(BulkWriter(DSN))

async def save_parsed_data(data: list[dict]):
    await bulk.insert_many(data)
