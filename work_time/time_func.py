import asyncio
import logging
from keyboards.user_keyboards import PARSING_CATEGORIES
from parser.main_parser import run_parsing

logger = logging.getLogger(__name__)


async def parse_all_categories_once(bot, db, chat_id: int | None = None) -> None:
    """Последовательно парсит все категории и сохраняет результаты в БД."""
    for category_name, category_id in PARSING_CATEGORIES.items():
        logger.info("Запущен плановый парсинг категории: %s", category_name)
        await run_parsing(
            bot=bot,
            chat_id=chat_id,
            category_id=category_id,
            category_name=category_name,
            db=db,
        )
        await asyncio.sleep(1)


async def parse_all_categories_hourly(bot, db, chat_id: int | None = None) -> None:
    """Запускает парсинг всех категорий каждый час."""
    while True:
        await parse_all_categories_once(bot=bot, db=db, chat_id=chat_id)
        await asyncio.sleep(3600)

