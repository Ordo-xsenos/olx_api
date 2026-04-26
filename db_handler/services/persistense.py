import logging
from typing import Dict, Iterable, List

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from config import settings
from db_handler.db.engine import SessionLocal
from db_handler.db.models import Product


def _chunked(items: List[Dict], size: int) -> Iterable[List[Dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def save_parsed_data(data: List[Dict]) -> None:
    if not data:
        return

    batch_size = settings.batch_size
    logger = logging.getLogger(__name__)

    async with SessionLocal() as session:
        try:
            total = 0
            for batch in _chunked(data, batch_size):
                stmt = insert(Product).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['url'],
                    set_={
                        'category': stmt.excluded.category,
                        'title': stmt.excluded.title,
                        'price': stmt.excluded.price,
                        'currency': stmt.excluded.currency,
                        'location': stmt.excluded.location,
                        'precise_location': stmt.excluded.precise_location,
                        'parameters': stmt.excluded.parameters,
                        'olx_id': func.coalesce(stmt.excluded.olx_id, Product.olx_id),
                    }
                )
                await session.execute(stmt)
                await session.commit()
                total += len(batch)
                logger.info("Сохранен пакет: %s элементов", len(batch))
            logger.info("Всего сохранено: %s элементов", total)
        except Exception as e:
            await session.rollback()
            logger.error("Ошибка сохранения данных: %s", e, exc_info=True)
            raise
