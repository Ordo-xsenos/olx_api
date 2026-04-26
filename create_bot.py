import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from middlewares.db_session import DbSessionMiddleware

scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
admins = [a.strip() for a in settings.admins.split(",") if a.strip()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(DbSessionMiddleware())
dp.callback_query.middleware(DbSessionMiddleware())
