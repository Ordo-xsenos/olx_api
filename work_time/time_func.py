import asyncio
from create_bot import logger, bot, pg_db


BROADCAST_TEXT = (
    "🎓 Salom, aziz ishtirokchilar!\n"
    "Ko‘pchilik allaqachon o‘z fakultetida jamoadoshlari bilan tanishib, faol muloqot boshlashdi. Sizchi?\n"
    "Agar fakultetni tanlab bo‘lgan bo‘lsangiz, biroq hali guruhga qo‘shilmagan bo‘lsangiz — shoshiling!\n\n"
    "O‘yinlar bo‘limiga o‘ting va o‘z fakultetingiz guruhini topib, jamoangizga qo‘shiling.\n"
    "Fakultet hayoti sizni kutmoqda! 🌟"
)

SEND_DELAY_SECONDS = 0.05


async def broadcast_text(text: str) -> dict:
    """Send text to all users. Returns report dict: {sent: n, failed: n, removed: [ids]}"""

    users = await pg_db.get_all_users()
    sent = 0
    failed = 0
    removed = []

    for user in users:
        user_id = user['user_id']
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception as exc:
            # Common reasons: Bot was blocked, chat deleted, user deactivated
            logger.warning("Failed to send to %s: %s", user_id, exc)
            failed += 1
            # try to remove obvious invalid chats
            try:
                removed.append(user_id)
            except Exception as e:
                logger.exception("Failed to remove user %s from DB: %s", user_id, e)
        await asyncio.sleep(SEND_DELAY_SECONDS)

    report = {"sent": sent, "failed": failed, "removed": removed}
    logger.info("Broadcast finished: %s", report)
    return report
