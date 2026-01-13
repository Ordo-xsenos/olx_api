import io
import os
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from db_handler.db.models import Product
from db_handler.db.engine import get_session_maker
from db_handler.storage.bulk import BulkWriter


load_dotenv(find_dotenv())
BASE_DIR = Path(__file__).resolve().parent.parent
DSN = os.getenv("DATABASE_URL")

async def save_parsed_data(data: list[dict]):
    async with get_session_maker() as session:
        await session.execute(text("TRUNCATE TABLE products RESTART IDENTITY;"))
        await session.commit()

    bulk_writer = BulkWriter()
    await bulk_writer.insert_many(data)


def create_excel_report_from_db(
    session: Session, category_name: str | None = None
    ) -> io.BytesIO:
    """
    Запрашивает объявления из БД и создает Excel-файл в памяти.
    Если указан `category_name`, фильтрует по нему.
    """
    query = session.query(Product)

    # Фильтруем по категории, если она указана
    if category_name:
        query = query.filter(Product.category == category_name)

    all_estates = query.all()

    if not all_estates:
        return io.BytesIO()

    data_list = [
        {
            "Категория": estate.category,
            "Название": estate.title,
            "Цена": estate.price,
            "Ссылка": estate.url,
        }
        for estate in all_estates
        ]
    df = pd.DataFrame(data_list)

    output_buffer = io.BytesIO()
    df.to_excel(output_buffer, index=False, engine='openpyxl')
    output_buffer.seek(0)

    return output_buffer