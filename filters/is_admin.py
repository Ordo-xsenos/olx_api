import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from db_handler.db.engine import SessionLocal
from db_handler.services.repository import (
    get_user_by_tg_id,
    get_user_by_username,
    upsert_user,
    promote_admin_if_username,
)


class IsAdmin(BaseFilter):
    async def __call__(self, event, **data) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            logging.getLogger(__name__).warning("IsAdmin: no from_user")
            return False

        # Создаем собственную сессию, так как фильтры выполняются до middleware
        async with SessionLocal() as session:
            record = await get_user_by_tg_id(session, user.id)
            if record and record.get("is_admin"):
                return True
            username = user.username.lower() if user.username else None
            if username:
                admin_by_name = await get_user_by_username(session, username)
                if admin_by_name and admin_by_name.get("is_admin"):
                    updated = await upsert_user(session, user.id, username)
                    if updated and not updated.get("is_admin"):
                        await promote_admin_if_username(session, user.id, username)
                    return True

        logging.getLogger(__name__).warning(
            "IsAdmin: denied tg_id=%s username=%s",
            user.id,
            user.username,
        )
        return False
