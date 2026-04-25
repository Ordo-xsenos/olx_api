"""
Фикстуры для тестов.
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup


# =============================================================================
# HTML Фикстуры
# =============================================================================

@pytest.fixture
def sample_category_html() -> str:
    """HTML страницы категории для тестов."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div data-testid="listing-grid" class="css-j0t2x2">
            <div data-testid="l-card" data-cy="l-card" class="css-1sw7q4x" id="123456">
                <a href="/d/obyavlenie/test-ID123.html">
                    <div data-testid="ad-card-title" class="css-u2ayx9">Тестовый товар</div>
                    <p data-testid="ad-price" class="css-blr5zl">100 000 сум</p>
                    <p data-testid="location-date" class="css-3cz5o2">Ташкент, 25 марта 2026 г.</p>
                </a>
            </div>
            <div data-testid="l-card" data-cy="l-card" class="css-1sw7q4x" id="789012">
                <a href="/d/obyavlenie/test-ID456.html">
                    <div data-testid="ad-card-title" class="css-u2ayx9">Другой товар</div>
                    <p data-testid="ad-price" class="css-blr5zl">200 $</p>
                    <p data-testid="location-date" class="css-3cz5o2">Самарканд, 26 марта 2026 г.</p>
                </a>
            </div>
        </div>
        <ul data-testid="pagination-list">
            <li><a href="?page=1">1</a></li>
            <li><a href="?page=2">2</a></li>
        </ul>
    </body>
    </html>
    """


@pytest.fixture
def sample_product_html() -> str:
    """HTML страницы товара для тестов."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1 data-testid="heading" class="css-xl2heb">Тестовый товар</h1>
        <p data-testid="ad-price" class="css-yauxmy">100 000 сум</p>
        <span data-testid="ad-posted-at" class="css-1br3d2a">25 марта 2026 г.</span>
        <div class="css-1deibjd">
            <p class="css-9pna1a">ул. Тестовая, 123</p>
            <p class="css-3cz5o2">Ташкент</p>
        </div>
        <div class="css-6zsv65">
            <p class="css-13x8d99">Параметр 1: Значение 1</p>
            <p class="css-13x8d99">Параметр 2: Значение 2</p>
        </div>
        <span class="css-ooacec">12345678</span>
    </body>
    </html>
    """


@pytest.fixture
def sample_soup(sample_category_html: str) -> BeautifulSoup:
    """BeautifulSoup для тестов."""
    return BeautifulSoup(sample_category_html, "html.parser")


# =============================================================================
# Фикстуры данных
# =============================================================================

@pytest.fixture
def sample_product_data() -> dict[str, Any]:
    """Пример данных товара."""
    return {
        "id": 123456,
        "title": "Тестовый товар",
        "price": 100000,
        "currency": "UZS",
        "location": "Ташкент",
        "precise_location": "ул. Тестовая, 123",
        "url": "https://www.olx.uz/d/obyavlenie/test-ID123.html",
        "category": "nedvizhimost",
        "created_at": datetime(2026, 3, 25, 10, 0, 0),
    }


@pytest.fixture
def sample_products_list(sample_product_data: dict) -> list[dict]:
    """Список товаров для тестов."""
    return [sample_product_data]


@pytest.fixture
def sample_product_with_datetime(sample_product_data: dict) -> dict:
    """Товар с datetime объектом (для тестов сериализации)."""
    data = sample_product_data.copy()
    data["created_at"] = datetime(2026, 3, 25, 10, 30, 0)
    data["price"] = Decimal("100000.50")
    return data


# =============================================================================
# Фикстуры для моков БД
# =============================================================================

@pytest.fixture
def mock_db_session() -> MagicMock:
    """Мокированная сессия БД."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """Мокированная асинхронная сессия."""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_postgres_handler() -> MagicMock:
    """Мокированный PostgresHandler."""
    handler = MagicMock()
    handler.fetch_query = AsyncMock()
    handler.fetchrow_query = AsyncMock()
    handler.execute_query = AsyncMock()
    return handler


# =============================================================================
# Фикстуры для моков HTTP
# =============================================================================

@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Мокированный httpx клиент."""
    client = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Мокированный HTTP ответ."""
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"status": "ok"}'
    response.json.return_value = {"status": "ok"}
    response.text = '{"status": "ok"}'
    response.raise_for_status = MagicMock()
    return response


# =============================================================================
# Фикстуры для моков бота
# =============================================================================

@pytest.fixture
def mock_bot() -> AsyncMock:
    """Мокированный aiogram бот."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_document = AsyncMock()
    bot.delete_webhook = AsyncMock()
    return bot


@pytest.fixture
def mock_message() -> MagicMock:
    """Мокированное сообщение."""
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.text = "/latest 10"
    return message


@pytest.fixture
def mock_callback() -> MagicMock:
    """Мокированный callback query."""
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.answer_document = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    return callback


# =============================================================================
# Фикстуры для окружения
# =============================================================================

@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Мокирование переменных окружения."""
    monkeypatch.setenv("WEBHOOK_URL", "https://test-webhook.site/test")
    monkeypatch.setenv("CLEANUP_MISSING", "1")
    monkeypatch.setenv("WEBHOOK_TIMEOUT_SECONDS", "10")


@pytest.fixture
def mock_env_no_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    """Мокирование без вебхука."""
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.setenv("CLEANUP_MISSING", "0")


# =============================================================================
# Утилиты для тестов
# =============================================================================

@pytest.fixture
def sample_selectors() -> dict[str, list[dict]]:
    """Пример селекторов для тестов."""
    return {
        "product_card": [
            {"data-testid": "l-card"},
            {"class_": "css-1sw7q4x"},
        ],
        "product_title": [
            {"data-testid": "ad-card-title"},
            {"class_": "css-u2ayx9"},
            {"tag": "h3"},
        ],
    }
