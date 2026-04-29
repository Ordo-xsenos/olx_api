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


def _deduplicate_by_url(items: List[Dict]) -> List[Dict]:
    deduplicated: List[Dict] = []
    seen_urls: set[str] = set()
    items_without_url: List[Dict] = []

    for item in reversed(items):
        url = item.get("url")
        if not url:
            items_without_url.append(item)
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduplicated.append(item)

    deduplicated.reverse()
    items_without_url.reverse()
    return [*items_without_url, *deduplicated]


async def save_parsed_data(data: List[Dict]) -> None:
    if not data:
        return

    batch_size = settings.batch_size
    logger = logging.getLogger(__name__)
    prepared_data = _deduplicate_by_url(data)

    duplicates_removed = len(data) - len(prepared_data)
    if duplicates_removed > 0:
        logger.warning(
            "Удалены дубли перед сохранением: %s записей с одинаковым url",
            duplicates_removed,
        )

    async with SessionLocal() as session:
        try:
            total = 0
            for batch in _chunked(prepared_data, batch_size):
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
