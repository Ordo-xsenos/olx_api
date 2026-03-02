import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def send_webhook(
    client: httpx.AsyncClient,
    data: list[dict[str, Any]] | dict[str, Any],
    url: str,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | str | None:
    logger.info("Отправка вебхука на %s...", url)
    response = await client.post(url, json=data, headers=headers)
    response.raise_for_status()

    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


async def webhook_client(
    data: list[dict[str, Any]] | dict[str, Any],
    url: str,
    event_id: str | None = None,
) -> dict[str, Any] | str | None:
    headers = {
        "Idempotency-Key": event_id or "",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        return await send_webhook(client, data, url, headers)
