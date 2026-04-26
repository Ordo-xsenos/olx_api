import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Получить глобальный HTTP клиент."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; olx-scraper/2.0)"},
            follow_redirects=True
        )
    return _client


async def close_http_client() -> None:
    """Закрыть глобальный HTTP клиент."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
