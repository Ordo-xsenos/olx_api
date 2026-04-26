import asyncio
import logging
import time

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from db_handler.db.engine import SessionLocal
from db_handler.main import Filters
from db_handler.services.outbox_service import enqueue_webhook
from db_handler.services.webhook_serializer import serialize_for_webhook
from db_handler.services.repository import (
    get_allow_non_admins,
    get_stats,
    get_user_by_tg_id,
    list_latest_products,
    list_products_for_export,
    list_users,
    mark_admin_by_username,
    promote_admin_if_username,
    delete_user_by_username,
    delete_user_by_tg_id,
    set_ban_with_reason,
    set_allow_non_admins,
    upsert_user,
)
from export.excel import build_excel
from filters.is_admin import IsAdmin
from keyboards.user_keyboards import (
    PARSING_CATEGORIES,
    get_parsing_categories_keyboard,
    get_report_categories_keyboard,
    get_configurator_keyboard,
)
from parser.main_parser import run_parsing

start_router = Router()

class ParseConfigurator(StatesGroup):
    configuring = State()
    waiting_for_min_price = State()
    waiting_for_max_price = State()
    waiting_for_city = State()
    waiting_for_keyword = State()
    waiting_for_custom_url = State()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)


def _extract_username(text: str) -> str | None:
    parts = text.split()
    if len(parts) < 2:
        return None
    username = parts[1].strip()
    if username.startswith("@"):
        username = username[1:]
    return username or None


async def _ensure_user(session: AsyncSession, user) -> bool:
    username = user.username or None
    record = await upsert_user(session, user.id, username)
    if record and not record.get("is_admin"):
        promoted = await promote_admin_if_username(session, user.id, username)
        if promoted:
            record["is_admin"] = True
    if record and record.get("is_banned"):
        return False
    allow_non_admins = await _get_allow_non_admins_cached(session)
    if not allow_non_admins and not (record and record.get("is_admin")):
        return False
    return True


_allow_cache = {"value": None, "ts": 0.0}


async def _get_allow_non_admins_cached(session: AsyncSession) -> bool:
    now = time.time()
    if _allow_cache["value"] is None or now - _allow_cache["ts"] > 30:
        _allow_cache["value"] = await get_allow_non_admins(session)
        _allow_cache["ts"] = now
    return bool(_allow_cache["value"])


@start_router.message(Command("start"))
async def start_command_handler(message: Message, session: AsyncSession) -> None:
    if not await _ensure_user(session, message.from_user):
        await message.answer("Доступ к боту ограничен.")
        return
    await message.answer(
        "Привет! Добро пожаловать в бот.\n\n"
        "▶️ Для запуска парсинга отправьте команду /parse.\n"
        "📄 Для получения отчета отправьте команду /report.\n"
        "🆕 Для просмотра последних объявлений отправьте /latest."
    )


@start_router.message(Command("parse"))
async def parse_command_handler(message: Message, session: AsyncSession) -> None:
    if not await _ensure_user(session, message.from_user):
        await message.answer("Доступ к боту ограничен.")
        return
    await message.answer(
        "Выберите категорию для парсинга:",
        reply_markup=get_parsing_categories_keyboard(),
    )


@start_router.message(Command("report"))
async def report_command_handler(message: Message, session: AsyncSession) -> None:
    if not await _ensure_user(session, message.from_user):
        await message.answer("Доступ к боту ограничен.")
        return
    await message.answer(
        "Выберите категорию для отчета:",
        reply_markup=get_report_categories_keyboard(),
    )


@start_router.message(Command("latest"))
async def latest_command_handler(message: Message, session: AsyncSession) -> None:
    if not await _ensure_user(session, message.from_user):
        await message.answer("Доступ к боту ограничен.")
        return
    parts = message.text.split()
    limit = 10
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
    rows = await list_latest_products(session, limit=limit)
    if not rows:
        await message.answer("Пока нет сохраненных объявлений.")
        return

    lines = []
    for item in rows:
        price = item.get("price")
        currency = item.get("currency") or ""
        price_text = f"{price} {currency}".strip() if price is not None else "Цена не указана"
        lines.append(f"• {item.get('title')}\n{price_text}\n{item.get('url')}")
    await message.answer("\n\n".join(lines))

    # Отправка вебхука
    if settings.webhook_url:
        async with SessionLocal() as webhook_session:
            serialized_rows = serialize_for_webhook(rows)
            await enqueue_webhook(webhook_session, settings.webhook_url, serialized_rows)


@start_router.message(Command("filters"))
async def filters_command_handler(message: Message, session: AsyncSession) -> None:
    if not await _ensure_user(session, message.from_user):
        await message.answer("Доступ к боту ограничен.")
        return
    await message.answer(
        "Фильтры для выборки:\n"
        "• /latest N — последние N объявлений\n"
        "• /report — отчет по выбранной категории"
    )


@start_router.callback_query(F.data.startswith("parse_category:"))
async def process_category_callback(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    if not await _ensure_user(session, callback.from_user):
        await callback.message.answer("Доступ к боту ограничен.")
        await callback.answer()
        return
    category_id = callback.data.split(":", 1)[1]
    category_name = next(
        (k for k, v in PARSING_CATEGORIES.items() if v == category_id),
        category_id,
    )

    await state.clear()
    await state.update_data(
        category_id=category_id,
        category_name=category_name,
        min_price=None,
        max_price=None,
        city=None,
        keyword=None,
        custom_url=None,
    )
    await state.set_state(ParseConfigurator.configuring)

    await callback.message.edit_text(
        f"⚙️ Настройка парсинга для категории: <b>{category_name}</b>\n\n"
        "Вы можете настроить фильтры или сразу запустить парсинг.\n"
        "<i>Фильтры цены и Custom URL передаются напрямую в OLX.\n"
        "Город и ключевое слово фильтруются локально.</i>",
        reply_markup=get_configurator_keyboard({}),
    )
    await callback.answer()


@start_router.callback_query(ParseConfigurator.configuring, F.data.startswith("config:"))
async def process_config_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    action = callback.data.split(":", 1)[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Парсинг отменен.")
        await callback.answer()
        return

    if action == "start":
        data = await state.get_data()
        await callback.message.edit_text(
            f"🚀 Начинаю парсинг категории «<b>{data['category_name']}</b>» с учетом фильтров.\n"
            "Это может занять несколько минут. Я пришлю уведомление по завершении."
        )
        await callback.answer()

        # Сбор параметров для URL
        url_params_list = []
        if data.get("min_price"):
            url_params_list.append(f"search[filter_float_price:from]={data['min_price']}")
        if data.get("max_price"):
            url_params_list.append(f"search[filter_float_price:to]={data['max_price']}")
        if data.get("custom_url"):
            url_params_list.append(data["custom_url"].lstrip("?&"))

        url_params = "&".join(url_params_list)

        # Сбор локальных фильтров
        local_filters = Filters()
        has_local = False
        if data.get("city"):
            local_filters.city(data["city"])
            has_local = True
        if data.get("keyword"):
            local_filters.keyword(data["keyword"])
            has_local = True

        asyncio.create_task(
            run_parsing(
                bot=callback.bot,
                chat_id=callback.from_user.id,
                category_id=data["category_id"],
                category_name=data["category_name"],
                db=None,
                url_params=url_params,
                local_filters=local_filters if has_local else None,
            )
        )
        await state.clear()
        return

    # Переход в состояния ожидания ввода
    state_map = {
        "set_min_price": ParseConfigurator.waiting_for_min_price,
        "set_max_price": ParseConfigurator.waiting_for_max_price,
        "set_city": ParseConfigurator.waiting_for_city,
        "set_keyword": ParseConfigurator.waiting_for_keyword,
        "set_custom_url": ParseConfigurator.waiting_for_custom_url,
    }

    prompt_map = {
        "set_min_price": "💰 Введите <b>минимальную цену</b> (только цифры) или 0 чтобы сбросить:",
        "set_max_price": "💰 Введите <b>максимальную цену</b> (только цифры) или 0 чтобы сбросить:",
        "set_city": "🏙 Введите <b>город</b> для локальной фильтрации (например: Ташкент):",
        "set_keyword": "📝 Введите <b>ключевое слово</b> для поиска в заголовке:",
        "set_custom_url": "🔗 Введите <b>параметры URL</b> (например: search[order]=created_at:desc):",
    }

    if action in state_map:
        await state.set_state(state_map[action])
        await callback.message.answer(prompt_map[action])
        await callback.answer()


@start_router.message(ParseConfigurator.waiting_for_min_price)
@start_router.message(ParseConfigurator.waiting_for_max_price)
@start_router.message(ParseConfigurator.waiting_for_city)
@start_router.message(ParseConfigurator.waiting_for_keyword)
@start_router.message(ParseConfigurator.waiting_for_custom_url)
async def process_config_input(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    text = message.text.strip() if message.text else ""

    if text.lower() in ["пропустить", "skip", "нет"]:
        text = None
    elif text == "0":
        text = None

    if current_state == ParseConfigurator.waiting_for_min_price.state:
        if text and not text.isdigit():
            await message.answer("⚠️ Пожалуйста, введите только цифры.")
            return
        await state.update_data(min_price=text)
    elif current_state == ParseConfigurator.waiting_for_max_price.state:
        if text and not text.isdigit():
            await message.answer("⚠️ Пожалуйста, введите только цифры.")
            return
        await state.update_data(max_price=text)
    elif current_state == ParseConfigurator.waiting_for_city.state:
        await state.update_data(city=text)
    elif current_state == ParseConfigurator.waiting_for_keyword.state:
        await state.update_data(keyword=text)
    elif current_state == ParseConfigurator.waiting_for_custom_url.state:
        await state.update_data(custom_url=text)

    await state.set_state(ParseConfigurator.configuring)
    data = await state.get_data()
    await message.answer(
        f"⚙️ Настройка для: <b>{data['category_name']}</b>",
        reply_markup=get_configurator_keyboard(data)
    )


@start_router.callback_query(F.data.startswith("report_category:"))
async def process_report_callback(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    if not await _ensure_user(session, callback.from_user):
        await callback.message.answer("Доступ к боту ограничен.")
        await callback.answer()
        return
    category_id = callback.data.split(":", 1)[1]
    rows = await list_products_for_export(session, category=category_id)
    if not rows:
        await callback.message.answer("По выбранной категории нет данных.")
        await callback.answer()
        return

    report = build_excel(rows)
    if category_id == "all":
        filename = "all_category_report.xlsx"
    else:
        normalized = category_id.strip("/ ")
        filename = f"{normalized}_report.xlsx"
    file = BufferedInputFile(report.getvalue(), filename=filename)
    await callback.message.answer_document(file)
    await callback.answer()


@start_router.message(IsAdmin(), Command("add_admin"))
async def add_admin_command(message: Message, session: AsyncSession) -> None:
    username = _extract_username(message.text)
    if not username:
        await message.answer("Укажи ник: /add_admin @username")
        return
    await mark_admin_by_username(session, username)
    await message.answer(f"Админ добавлен: @{username}")


@start_router.message(IsAdmin(), Command("ban"))
async def ban_command(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Укажи ник: /ban @username [причина]")
        return
    username = parts[1].strip().lstrip("@")
    reason = parts[2].strip() if len(parts) == 3 else "manual"
    await set_ban_with_reason(session, username, True, reason)
    await message.answer(f"Пользователь заблокирован: @{username}")


@start_router.message(IsAdmin(), Command("unban"))
async def unban_command(message: Message, session: AsyncSession) -> None:
    username = _extract_username(message.text)
    if not username:
        await message.answer("Укажи ник: /unban @username")
        return
    await set_ban_with_reason(session, username, False, None)
    await message.answer(f"Пользователь разблокирован: @{username}")


@start_router.message(IsAdmin(), Command("stats"))
async def stats_command(message: Message, session: AsyncSession) -> None:
    stats = await get_stats(session)
    await message.answer(
        "Статистика:\n"
        f"• Объявлений: {stats.get('products')}\n"
        f"• Пользователей: {stats.get('users')}\n"
        f"• Админов: {stats.get('admins')}\n"
        f"• Заблокированных: {stats.get('banned')}"
    )


@start_router.message(IsAdmin(), Command("users"))
async def users_command(message: Message, session: AsyncSession) -> None:
    rows = await list_users(session)
    if not rows:
        await message.answer("Список пользователей пуст.")
        return
    lines = []
    for row in rows:
        uname = row.get("username") or "no_username"
        flags = []
        if row.get("is_admin"):
            flags.append("admin")
        if row.get("is_banned"):
            reason = row.get("ban_reason") or "banned"
            flags.append(reason)
        flags_text = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"@{uname}{flags_text}")
    await message.answer("\n".join(lines))


@start_router.message(IsAdmin(), Command("del_user"))
async def del_user_command(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи ник: /del_user @username")
        return
    username = parts[1].strip()
    deleted = await delete_user_by_username(session, username)
    await message.answer(f"Удалено записей: {deleted}")


@start_router.message(IsAdmin(), Command("del_user_id"))
async def del_user_id_command(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Укажи tg_id: /del_user_id 123456789")
        return
    deleted = await delete_user_by_tg_id(session, int(parts[1]))
    await message.answer(f"Удалено записей: {deleted}")


@start_router.message(Command("whoami"))
async def whoami_command(message: Message, session: AsyncSession) -> None:
    record = await upsert_user(session, message.from_user.id, message.from_user.username)
    if not record:
        record = await get_user_by_tg_id(session, message.from_user.id)
    allow_non_admins = await _get_allow_non_admins_cached(session)
    if not record:
        await message.answer("Пользователь не найден в БД.")
        return
    await message.answer(
        "Профиль:\n"
        f"• tg_id: {record.get('tg_id')}\n"
        f"• username: @{record.get('username')}\n"
        f"• admin: {record.get('is_admin')}\n"
        f"• banned: {record.get('is_banned')}\n"
        f"• allow_non_admins: {allow_non_admins}"
    )


@start_router.message(IsAdmin(), Command("allow_all"))
async def allow_all_command(message: Message, session: AsyncSession) -> None:
    await set_allow_non_admins(session, True)
    await message.answer("Доступ для неадминов разрешен.")


@start_router.message(IsAdmin(), Command("deny_all"))
async def deny_all_command(message: Message, session: AsyncSession) -> None:
    await set_allow_non_admins(session, False)
    await message.answer("Доступ для неадминов запрещен.")
