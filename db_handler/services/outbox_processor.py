import logging
import os
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db_handler.db.engine import SessionLocal
from db_handler.db.models import OutboxStatus, WebhookOutbox
from db_handler.services.webhook_client import send_webhook

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30


async def process_outbox() -> None:
    """
    Забирает pending-события из outbox и пытается их доставить.
    """
    try:
        timeout_seconds = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "10"))
        async with SessionLocal() as session:
            stmt = (
                select(WebhookOutbox)
                .where(
                    WebhookOutbox.status == OutboxStatus.PENDING,
                    WebhookOutbox.next_retry_at <= datetime.utcnow(),
                )
                .limit(50)
            )
            result = await session.execute(stmt)
            events = result.scalars().all()

            if not events:
                return

            logger.info("Outbox: найдено %s событий для доставки", len(events))

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_seconds)
            ) as client:
                for event in events:
                    await deliver_event(session, client, event)

            await session.commit()
    except Exception:
        logger.exception("Outbox: необработанная ошибка в process_outbox")


async def deliver_event(
    session: AsyncSession,
    client: httpx.AsyncClient,
    event: WebhookOutbox,
) -> None:
    """
    Доставляет одно событие.
    """
    headers = {
        "Idempotency-Key": str(event.id),
        "Content-Type": "application/json",
    }
    try:
        await send_webhook(
            client=client,
            data=event.payload,
            url=event.target_url,
            headers=headers,
        )
        event.status = OutboxStatus.SENT
        event.last_error = None
        logger.info("Outbox: событие %s доставлено", event.id)
    except Exception as exc:
        event.attempts += 1
        event.last_error = str(exc)

        if event.attempts >= MAX_ATTEMPTS:
            event.status = OutboxStatus.DEAD
            logger.error(
                "Outbox: событие %s помечено DEAD после %s попыток",
                event.id,
                event.attempts,
            )
            return

        backoff = BASE_BACKOFF_SECONDS * event.attempts
        event.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
        event.status = OutboxStatus.PENDING
        logger.warning(
            "Outbox: ошибка доставки %s. Попытка %s. Повтор через %s сек.",
            event.id,
            event.attempts,
            backoff,
        )
