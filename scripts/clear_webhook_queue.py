import asyncio
import os
from dotenv import load_dotenv

from db_handler.db.engine import SessionLocal
from db_handler.db.models import WebhookOutbox, OutboxStatus
from sqlalchemy import delete

load_dotenv()


async def clear_pending_webhooks():
    """Очищает очередь webhook от старых записей со старым URL."""
    async with SessionLocal() as session:
        # Удаляем все pending вебхуки
        stmt = delete(WebhookOutbox).where(
            WebhookOutbox.status == OutboxStatus.PENDING
        )
        result = await session.execute(stmt)
        await session.commit()
        print(f"Удалено {result.rowcount} pending вебхуков из очереди")


if __name__ == "__main__":
    asyncio.run(clear_pending_webhooks())
