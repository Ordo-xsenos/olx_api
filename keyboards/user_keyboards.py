from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
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