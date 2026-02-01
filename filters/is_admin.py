import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

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
        db = data.get("db")
        if db is None:
            logging.getLogger(__name__).warning("IsAdmin: no db in data")
            return False
        record = await get_user_by_tg_id(db, user.id)
        if record and record.get("is_admin"):
            return True
        username = user.username.lower() if user.username else None
        if username:
            admin_by_name = await get_user_by_username(db, username)
            if admin_by_name and admin_by_name.get("is_admin"):
                updated = await upsert_user(db, user.id, username)
                if updated and not updated.get("is_admin"):
                    await promote_admin_if_username(db, user.id, username)
                return True
        logging.getLogger(__name__).warning(
            "IsAdmin: denied tg_id=%s username=%s",
            user.id,
            user.username,
        )
        return False
