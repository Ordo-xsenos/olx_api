from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

def get_parsing_categories_keyboard() -> InlineKeyboardMarkup:
    """
    Создает и возвращает inline-клавиатуру с категориями для парсинга.
    """
    builder = InlineKeyboardBuilder()
    for text, callback_data in PARSING_CATEGORIES.items():
        builder.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"parse_category:{callback_data}",
            )
        )
    builder.adjust(2)
    return builder.as_markup()


def get_report_categories_keyboard():
    """
    Создает клавиатуру для выбора категории отчета.
    """
    buttons = []

    for name, category_id in PARSING_CATEGORIES.items():
        buttons.append(
            [InlineKeyboardButton(text=name, callback_data=f"report_category:{category_id}")]
        )

    buttons.append(
        [InlineKeyboardButton(text="📥 Все категории", callback_data="report_category:all")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_configurator_keyboard(config_data: dict) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для конфигурации фильтров перед парсингом.
    """
    min_p = config_data.get("min_price") or "Не задано"
    max_p = config_data.get("max_price") or "Не задано"
    city = config_data.get("city") or "Не задано"
    keyword = config_data.get("keyword") or "Не задано"
    custom_url = config_data.get("custom_url")
    custom_url_display = (custom_url[:15] + "...") if custom_url and len(custom_url) > 15 else (custom_url or "Не задано")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"💰 Мин. Цена: {min_p}", callback_data="config:set_min_price"))
    builder.row(InlineKeyboardButton(text=f"💰 Макс. Цена: {max_p}", callback_data="config:set_max_price"))
    builder.row(InlineKeyboardButton(text=f"🏙 Город: {city}", callback_data="config:set_city"))
    builder.row(InlineKeyboardButton(text=f"📝 Ключ. слово: {keyword}", callback_data="config:set_keyword"))
    builder.row(InlineKeyboardButton(text=f"🔗 Custom URL: {custom_url_display}", callback_data="config:set_custom_url"))
    builder.row(InlineKeyboardButton(text="▶️ Запустить парсинг", callback_data="config:start"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="config:cancel"))

    return builder.as_markup()
