from sqlalchemy.util import await_fallback
from db_handler.storage.bulk import BulkWriter
import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

load_dotenv(find_dotenv())
BASE_DIR = Path(__file__).resolve().parent.parent
DSN = os.getenv("DATABASE_URL")
bulk = await_fallback(BulkWriter())

async def save_parsed_data(data: list[dict]):
    await bulk.insert_many(data)
