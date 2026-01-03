import asyncio
from create_bot import bot, dp, scheduler
from create_bot import pg_db
from work_time.time_func import broadcast_text, BROADCAST_TEXT


async def main():
    await pg_db.create_pool()
    await pg_db.init_database()
    scheduler.add_job(broadcast_text, 'cron', day=1, hour=9, kwargs={'text': BROADCAST_TEXT})
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
