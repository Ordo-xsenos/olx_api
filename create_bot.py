import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from decouple import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db_handler.db_class import PostgresHandler
from middlewares.data import DbMiddleware

pg_db = PostgresHandler(dsn=config('DATABASE_URL'))
scheduler = AsyncIOScheduler(timezone='Asia/Tashkent')
admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=config('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(DbMiddleware(pg_db))
dp.callback_query.middleware(DbMiddleware(pg_db))

from handlers.start import start_router  # импортируем после создания bot и dp

dp.include_router(start_router)