from sqlalchemy.ext.asyncio import AsyncSession
from db_handler.db.models import WebhookOutbox
from typing import Any


async def enqueue_webhook(
    session: AsyncSession,
    target_url: str,
    payload: dict[str, Any] | list[dict[str, Any]],
) -> None:
    """
    Добавляет вебхук в очередь outbox для последующей доставки.

    Args:
        session: асинхронная сессия SQLAlchemy
        target_url: URL для отправки вебхука
        payload: данные для отправки
    """
    event = WebhookOutbox(
        target_url=target_url,
        payload=payload,
    )
    session.add(event)
    await session.commit()
