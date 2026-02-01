import logging
import os
from typing import Dict, Iterable, List

from db_handler.storage.bulk import BulkWriter


def _chunked(items: List[Dict], size: int) -> Iterable[List[Dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def save_parsed_data(data: List[Dict]) -> None:
    if not data:
        return
    batch_size = int(os.getenv("BATCH_SIZE", "200"))
    writer = BulkWriter()
    logger = logging.getLogger(__name__)
    try:
        total = 0
        for batch in _chunked(data, batch_size):
            await writer.insert_many(batch)
            total += len(batch)
            logger.info("Batch saved: %s items", len(batch))
        logger.info("Total saved: %s items", total)
    finally:
        await writer.close()
