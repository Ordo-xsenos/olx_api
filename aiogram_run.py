import asyncio
import os

from dotenv import load_dotenv

from create_bot import bot, dp, scheduler
from create_bot import pg_db
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

load_dotenv()


async def main():
    await pg_db.create_pool()
    await pg_db.init_database()
    admins_raw = os.getenv("ADMINS", "")
    for entry in [a.strip() for a in admins_raw.split(",") if a.strip()]:
        if entry.isdigit():
            if not await get_user_by_tg_id(pg_db, int(entry)):
                await mark_admin_by_tg_id(pg_db, int(entry))
        else:
            username = entry[1:] if entry.startswith("@") else entry
            if not await get_user_by_username(pg_db, username):
                await mark_admin_by_username(pg_db, username)
    schedule_category = os.getenv("SCHEDULE_CATEGORY_ID")
    schedule_category_name = os.getenv("SCHEDULE_CATEGORY_NAME", schedule_category)
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    schedule_time = os.getenv("PARSE_SCHEDULE_TIME")  # формат: HH:MM
    if schedule_category and chat_id and schedule_time and ":" in schedule_time:
        hour, minute = schedule_time.split(":", 1)
        scheduler.add_job(
            run_parsing,
            "cron",
            hour=int(hour),
            minute=int(minute),
            args=[bot, int(chat_id), schedule_category, schedule_category_name, pg_db],
        )
    scheduler.add_job(
        parse_all_categories_once,
        "interval",
        hours=1,
        args=[bot, pg_db, None],
    )
    register_outbox_scheduler(scheduler)
    scheduler.start()
    dp.include_router(start_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Выход")
