from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Замени на ID твоего канала (должен начинаться с -100 для супергрупп/каналов)
CHANNEL_ID = "@Shayxontohur_TIM"  # или -1001234567890

# --- Добавлено: Список категорий для парсинга ---
# Ключ - название для кнопки, Значение - идентификатор для callback'а
PARSING_CATEGORIES = {
    "Детский мир": "/detskiy-mir/",
    "Недвижимость": "/nedvizhimost/",
    "Транспорт": "/transport/",
    "Работа": "/rabota/",
    "Животные": "/zhivotnoe/",
    "Дом и сад": "/dom-i-sad/",
    "Электроника": "/elektronika/",
    "Услуги": "/uslugi/",
    "Мода и стиль": "/moda-i-stil/",
    "Хобби, отдых и спорт": "/hobbi-otdyh-i-sport/",
    "Отдам даром": "/otdam-darom/",
    "Обмен": "/obmen-barter/",
    "От застройщика": "/nedvizhimost/from_developer/",
}


main = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📝 Fakultetga qoshilish"),
            KeyboardButton(text="📊 Reyting"),
        ],
        [
            KeyboardButton(text="ℹ️ Loyiha haqida"),
            KeyboardButton(text="❓ Yordam"),
        ],
        [
            KeyboardButton(text="⚙️ Sozlamalar"),
            KeyboardButton(text="🎮 O'yinlar"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Bo'limni tanlang...",
)


# --- Добавлено: Клавиатура для выбора категории парсинга ---
def get_parsing_categories_keyboard() -> InlineKeyboardMarkup:
    """
    Создает и возвращает inline-клавиатуру с категориями для парсинга.
    """
    builder = InlineKeyboardBuilder()
    for text, callback_data in PARSING_CATEGORIES.items():
        builder.add(
            InlineKeyboardButton(
                text=text,
                # Формируем callback_data,
                # чтобы потом его можно было легко разобрать
                # Префикс 'parse_category:'
                # поможет отличить эти колбэки от других
                callback_data=f"parse_category:{callback_data}",
            )
        )
    # Выставляем количество кнопок в ряду. Например, 2.
    builder.adjust(2)
    return builder.as_markup()


# Функция проверки подписки пользователя
async def check_user_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Проверяем статус пользователя в канале
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Obunani tekshirishda xatolik yuz berdi: {e}")
        return False
