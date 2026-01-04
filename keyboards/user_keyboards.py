from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# Замени на ID твоего канала (должен начинаться с -100 для супергрупп/каналов)
CHANNEL_ID = "@Shayxontohur_TIM"  # или -1001234567890

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


# Функция проверки подписки пользователя
async def check_user_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Проверяем статус пользователя в канале
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Obunani tekshirishda xatolik yuz berdi: {e}")
        return False
