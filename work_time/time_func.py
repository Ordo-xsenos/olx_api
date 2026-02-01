import asyncio
import logging
from keyboards.user_keyboards import PARSING_CATEGORIES
from parser.main_parser import run_parsing

logger = logging.getLogger(__name__)


async def parse_all_categories_once(bot, db, chat_id: int | None = None) -> None:
    """Parse all categories sequentially and save results to DB."""
    for category_name, category_id in PARSING_CATEGORIES.items():
        logger.info("Scheduled parsing started: %s", category_name)
        await run_parsing(
            bot=bot,
            chat_id=chat_id,
            category_id=category_id,
            category_name=category_name,
            db=db,
        )
        await asyncio.sleep(1)


async def parse_all_categories_hourly(bot, db, chat_id: int | None = None) -> None:
    """Run parsing for all categories every hour."""
    while True:
        await parse_all_categories_once(bot=bot, db=db, chat_id=chat_id)
        await asyncio.sleep(3600)

