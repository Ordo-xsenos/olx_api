import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

from aiogram import Bot

from config import settings
from db_handler.db.engine import SessionLocal
from db_handler.main import (
    extract_products_links,
    get_current_usd_rate,
    parse_product_details,
    parse_products_from_category,
)
from db_handler.services.outbox_service import enqueue_webhook
from db_handler.services.persistense import save_parsed_data
from db_handler.services.repository import delete_missing_by_category
from db_handler.services.webhook_serializer import serialize_for_webhook
from parser.normalizer import normalize_product


MAIN_URL = "https://www.olx.uz"
logger = logging.getLogger(__name__)


async def scrape_category_data(category_id: str, url_params: str = "") -> tuple[tuple[Any], int]:
    category_url = urljoin(MAIN_URL, category_id.lstrip("/"))
    if url_params:
        join_char = "&" if "?" in category_url else "?"
        category_url = f"{category_url}{join_char}{url_params.lstrip('?&')}"
    
    logger.info(f"Запуск парсинга URL: {category_url}")
    usd_rate = await get_current_usd_rate()
    products = await parse_products_from_category(category_url)
    product_links = extract_products_links(products)
    detail_tasks = [
        parse_product_details(link, usd_rate, category_url)
        for link in product_links
    ]
    return await asyncio.gather(*detail_tasks), len(product_links)


async def run_parsing(
    bot: Bot,
    chat_id: int | None,
    category_id: str,
    category_name: str,
    db=None,
    url_params: str = "",
    local_filters: Any = None,
) -> None:
    try:
        scraped_data, total_links = await scrape_category_data(category_id, url_params)
        normalized_rows = []
        parsed_urls: list[str] = []
        for item in scraped_data:
            normalized = normalize_product(item)
            if normalized:
                # Применяем локальные фильтры (Keyword, City)
                if local_filters and not local_filters.match(normalized):
                    logger.debug(
                        "Товар пропущен фильтром: %s (Локация: %s)",
                        normalized.get("title"),
                        normalized.get("location")
                    )
                    continue
                normalized_rows.append(normalized)
                parsed_urls.append(normalized["url"])

        if not normalized_rows:
            if chat_id is not None:
                await bot.send_message(
                    chat_id,
                    f"😕 По категории «{category_name}» ничего не найдено.",
                )
            return

        await save_parsed_data(normalized_rows)
        if settings.webhook_url:
            async with SessionLocal() as session:
                serialized_rows = serialize_for_webhook(normalized_rows)
                await enqueue_webhook(session, settings.webhook_url, serialized_rows)

        cleanup_enabled = settings.cleanup_missing == "1"
        if cleanup_enabled and db is not None:
            ratio = (len(parsed_urls) / total_links) if total_links else 0.0
            if ratio >= 0.9:
                deleted = await delete_missing_by_category(
                    db, category_id, parsed_urls
                )
                logger.info(
                    "Очистка удалила %s отсутствующих строк для категории %s",
                    deleted,
                    category_id,
                )
            else:
                logger.warning(
                    "Очистка пропущена: распарсено %s/%s (%.1f%%) < 90%%",
                    len(parsed_urls),
                    total_links,
                    ratio * 100,
                )

        if chat_id is not None:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Парсинг категории «{category_name}» завершен.\n\n"
                    "Теперь вы можете запросить отчет с помощью команды /report."
                ),
            )
    except Exception as e:
        if chat_id is not None:
            await bot.send_message(
                chat_id,
                (
                    f"❌ Произошла ошибка при парсинге категории «{category_name}».\n"
                    f"Техническая информация: {e}"
                ),
            )
