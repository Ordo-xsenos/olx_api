import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv
import logging
from keyboards.user_keyboards import (get_parsing_categories_keyboard,
                                      PARSING_CATEGORIES)
from parser.main_parser import run_parsing

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
    await message.answer(
             "Привет! Добро пожаловать в бот.\n\n"
             "▶️ Для запуска парсинга отправьте команду /parse.\n"
             "📄 Для получения отчета отправьте команду /report."
          )


# --- Добавлено: Хендлер для обработки нажатий на inline-кнопки ---
@start_router.callback_query(F.data.startswith("parse_category:"))
async def process_category_callback(callback: CallbackQuery):
    """
    Этот хендлер ловит нажатия на inline-кнопки с категориями.
    """
    # Извлекаем идентификатор категории из callback_data
    # Например, из "parse_category:realty" получим "realty"
    category_id = callback.data.split(":")[1]

    # Ищем читаемое имя категории в нашем словаре
    category_name = [k for k, v in PARSING_CATEGORIES.items()
                     if v == category_id][0]

    # Отвечаем пользователю, что задача принята
    await callback.message.answer(
        f"✅ Принято! Начинаю парсинг категории «{category_name}».\n"
        f"Это может занять несколько минут. "
        f"Я пришлю вам файл, как только закончу."
    )
    # Подтверждаем получение колбэка, чтобы убрать "часики" на кнопке
    await callback.answer()

    # --- Запуск парсинга в фоновом режиме ---
    # Это ключевой момент: мы запускаем долгую задачу парсинга
    # и не ждем ее завершения. Бот может продолжать работать.
    # Передаем объект bot, чтобы задача могла отправлять сообщения.
    asyncio.create_task(run_parsing(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        category_id=category_id,
        category_name=category_name
    ))