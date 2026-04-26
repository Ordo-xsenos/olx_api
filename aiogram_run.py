import asyncio
import logging

from config import settings
from create_bot import bot, dp, scheduler
from handlers.start import start_router
from work_time.time_func import parse_all_categories_once
from db_handler.services.repository import (
    get_user_by_tg_id,
    get_user_by_username,
    mark_admin_by_tg_id,
    mark_admin_by_username,
)
from parser.main_parser import run_parsing
from db_handler.scheduler.outbox_scheduler import register_outbox_scheduler
from db_handler.db.engine import async_engine, SessionLocal
from db_handler.db.models import Base
from db_handler.http_client import close_http_client

logger = logging.getLogger(__name__)


async def init_db():
    """Инициализация БД - создание таблиц если их нет."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await init_db()

    async with SessionLocal() as session:
        for entry in [a.strip() for a in settings.admins.split(",") if a.strip()]:
            if entry.isdigit():
                if not await get_user_by_tg_id(session, int(entry)):
                    await mark_admin_by_tg_id(session, int(entry))
            else:
                username = entry[1:] if entry.startswith("@") else entry
                if not await get_user_by_username(session, username):
                    await mark_admin_by_username(session, username)

    if settings.schedule_category_id and settings.telegram_chat_id and settings.parse_schedule_time and ":" in settings.parse_schedule_time:
        hour, minute = settings.parse_schedule_time.split(":", 1)
        scheduler.add_job(
            run_parsing,
            "cron",
            hour=int(hour),
            minute=int(minute),
            args=[bot, int(settings.telegram_chat_id), settings.schedule_category_id, settings.schedule_category_name, None],
        )
    scheduler.add_job(
        parse_all_categories_once,
        "interval",
        hours=1,
        args=[bot, None, None],
    )
    register_outbox_scheduler(scheduler)
    scheduler.start()
    dp.include_router(start_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await close_http_client()
        logger.info("HTTP клиент закрыт")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения, выход...")
