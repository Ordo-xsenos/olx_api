import asyncio
from create_bot import bot, dp, scheduler
from create_bot import pg_db
# from work_time.time_func import broadcast_text, BROADCAST_TEXT

# --- Добавлено: Импортируем роутер с нашими хендлерами ---
from handlers.start import start_router


async def main():
    await pg_db.create_pool()
    await pg_db.init_database()
    # scheduler.add_job(broadcast_text, 'cron', day=1, hour=9)
    scheduler.start()

    # --- Добавлено: Регистрируем роутер в диспетчере ---
    # Теперь диспетчер будет знать о хендлерах, которые мы создали
    dp.include_router(start_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
