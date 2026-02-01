import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config

from db_handler.db_class import PostgresHandler
from middlewares.data import DbMiddleware

raw_dsn = config("RAW_DSN", default=None)
if not raw_dsn:
    database_url = config("DATABASE_URL", default=None)
    if database_url:
        raw_dsn = database_url.replace("+asyncpg", "")
    else:
        raw_dsn = config("SPECIAL_FOR_TGBOT_DATABASE_URL", default=None)

pg_db = PostgresHandler(dsn=raw_dsn)
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
admins_raw = config("ADMINS", default="")
admins = [a.strip() for a in admins_raw.split(",") if a.strip()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot_token = config("TELEGRAM_BOT_TOKEN", default=config("TOKEN", default=""))
bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(DbMiddleware(pg_db))
dp.callback_query.middleware(DbMiddleware(pg_db))
dp["db"] = pg_db
