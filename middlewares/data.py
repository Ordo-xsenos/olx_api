from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Awaitable, Any, Dict

class DbMiddleware(BaseMiddleware):
    def __init__(self, db):
        super().__init__()
        self.db = db

    async def __call__(self, handler : Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event : TelegramObject, data : Dict[str, Any]) -> Any:
        data["db"] = self.db
        return await handler(event, data)
