from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv
import logging

load_dotenv()

start_router = Router()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(ch)

@start_router.message(Command("start"))
async def start_command_handler(message: Message):
    await message.answer("Salom! Botga xush kelibsiz.")