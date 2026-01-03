from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, user, \
    LinkPreviewOptions

# Замени на ID твоего канала (должен начинаться с -100 для супергрупп/каналов)
CHANNEL_ID = "@Shayxontohur_TIM"  # или -1001234567890

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='📝 Fakultetga qoshilish'),
     KeyboardButton(text='📊 Reyting')],
    [KeyboardButton(text='ℹ️ Loyiha haqida'),
     KeyboardButton(text='❓ Yordam')],
    [KeyboardButton(text='⚙️ Sozlamalar'),
     KeyboardButton(text='🎮 O\'yinlar'), ]

] ,resize_keyboard=True, input_field_placeholder='Bo\'limni tanlang...')

# Создаем inline клавиатуру с кнопкой подписки
async def create_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna boling", url=f"https://t.me/Shayxontohur_TIM")],
        [InlineKeyboardButton(text="✅ Obunani tekshiring", callback_data="check_subscription")],
        [InlineKeyboardButton(text="🎮 Asosiy guruh", url=f"https://t.me/PSU_Mafia")],
    ])
    return keyboard

# Функция проверки подписки пользователя
async def check_user_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Проверяем статус пользователя в канале
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Obunani tekshirishda xatolik yuz berdi: {e}")
        return False

async def create_faculty_url(faculty: str) -> InlineKeyboardMarkup:
    faculty_list = {'Gryffindor':'https://t.me/+YbYXza1MRCViNmVi', 'Hufflepuff':'https://t.me/+RX3X_EnrGdY5ZWVi', 'Ravenclaw':'https://t.me/+vKbkfxNmTTdkMzgy', 'Slytherin':'https://t.me/+RT6x82IdsPFhMGYy'}
    url = faculty_list[faculty]  # Замените на реальную ссылку для каждого факультета
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Fakultetingiz", url=url)]
    ])
    return keyboard