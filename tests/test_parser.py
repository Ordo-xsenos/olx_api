"""
Тесты для модуля db_handler/main.py (функции парсинга)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from db_handler.main import (
    extract_products_links,
    get_text_or_default,
    get_total_pages,
    normalize_listing_url,
    parse_price_value,
    parse_product_details,
    parse_products_from_category,
)


class TestNormalizeListingUrl:
    """Тесты функции normalize_listing_url."""

    def test_remove_query_params(self) -> None:
        """Удаление query параметров."""
        url = "https://www.olx.uz/d/obyavlenie/test-ID123.html?sort=desc&page=1"
        result = normalize_listing_url(url)
        assert result == "https://www.olx.uz/d/obyavlenie/test-ID123.html"

    def test_remove_trailing_slash(self) -> None:
        """Удаление завершающего слэша."""
        url = "https://www.olx.uz/nedvizhimost/"
        result = normalize_listing_url(url)
        assert result == "https://www.olx.uz/nedvizhimost"

    def test_preserve_clean_url(self) -> None:
        """Сохранение чистого URL."""
        url = "https://www.olx.uz/d/obyavlenie/test-ID123.html"
        result = normalize_listing_url(url)
        assert result == url

    def test_remove_fragment(self) -> None:
        """Удаление фрагмента."""
        url = "https://www.olx.uz/test#anchor"
        result = normalize_listing_url(url)
        assert "#" not in result


class TestGetTextOrDefault:
    """Тесты функции get_text_or_default."""

    def test_get_text_from_tag(self) -> None:
        """Извлечение текста из тега."""
        soup = BeautifulSoup("<div class='test'>Hello</div>", "html.parser")
        result = get_text_or_default(soup, "div", "test")
        assert result == "Hello"

    def test_get_text_default_when_not_found(self) -> None:
        """Возврат default когда тег не найден."""
        soup = BeautifulSoup("<div>Test</div>", "html.parser")
        result = get_text_or_default(soup, "span", "nonexistent", default="Default")
        assert result == "Default"

    def test_get_text_from_string_parent(self) -> None:
        """Извлечение текста из строки."""
        result = get_text_or_default("  Test String  ", "div", "test")
        assert result == "Test String"

    def test_get_text_empty_parent(self) -> None:
        """Возврат default для пустого parent."""
        result = get_text_or_default(None, "div", "test", default="Default")
        assert result == "Default"


class TestParsePriceValue:
    """Тесты функции parse_price_value."""

    def test_parse_uzs_price(self) -> None:
        """Парсинг цены в сумах."""
        text = "100 000 сум"
        value, currency = parse_price_value(text)
        assert value == 100000
        assert currency == "UZS"

    def test_parse_usd_price(self) -> None:
        """Парсинг цены в долларах."""
        text = "500 $"
        value, currency = parse_price_value(text)
        assert value == 500
        assert currency == "USD"

    def test_parse_negotiable_price(self) -> None:
        """Парсинг договорной цены."""
        text = "Договорная"
        value, currency = parse_price_value(text)
        assert value is None
        assert currency == "NEGOTIABLE"

    def test_parse_empty_text(self) -> None:
        """Парсинг пустого текста."""
        value, currency = parse_price_value("")
        assert value is None
        assert currency == "UNKNOWN"

    def test_parse_price_with_comma(self) -> None:
        """Парсинг цены с запятой."""
        text = "100,50 сум"
        value, currency = parse_price_value(text)
        assert value == 100.50
        assert currency == "UZS"

    def test_parse_price_with_non_breaking_space(self) -> None:
        """Парсинг цены с неразрывным пробелом."""
        text = "100\u00a0000 сум"
        value, currency = parse_price_value(text)
        assert value == 100000
        assert currency == "UZS"


class TestGetTotalPages:
    """Тесты функции get_total_pages."""

    def test_get_total_pages_from_pagination(self) -> None:
        """Получение количества страниц из пагинации."""
        html = """
        <ul data-testid="pagination-list">
            <li><a href="?page=1">1</a></li>
            <li><a href="?page=2">2</a></li>
            <li><a href="?page=3">3</a></li>
        </ul>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = get_total_pages(soup)
        assert result == 3

    def test_get_total_pages_no_pagination(self) -> None:
        """Когда пагинация отсутствует."""
        soup = BeautifulSoup("<div>No pagination</div>", "html.parser")
        result = get_total_pages(soup)
        assert result == 1

    def test_get_total_pages_with_arrow(self) -> None:
        """Когда последняя страница со стрелкой."""
        html = """
        <ul data-testid="pagination-list">
            <li><a href="?page=1">1</a></li>
            <li><a href="?page=2">2</a></li>
            <li><a href="?page=3">&gt;</a></li>
        </ul>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = get_total_pages(soup)
        assert result == 2


class TestExtractProductsLinks:
    """Тесты функции extract_products_links."""

    def test_extract_links_from_cards(
        self, sample_soup: BeautifulSoup
    ) -> None:
        """Извлечение ссылок из карточек товаров."""
        cards = sample_soup.find_all(attrs={"data-testid": "l-card"})
        links = extract_products_links(cards)

        assert len(links) == 2
        assert "www.olx.uz/d/obyavlenie/test-ID123.html" in links[0]
        assert "www.olx.uz/d/obyavlenie/test-ID456.html" in links[1]

    def test_extract_links_empty_list(self) -> None:
        """Извлечение ссылок из пустого списка."""
        links = extract_products_links([])
        assert links == []

    def test_extract_links_relative_urls(self) -> None:
        """Извлечение ссылок с относительными URL."""
        soup = BeautifulSoup(
            '<div><a href="/d/obyavlenie/test.html">Link</a></div>', "html.parser"
        )
        links = extract_products_links([soup])
        assert links[0].startswith("https://www.olx.uz")


class TestParseProductDetails:
    """Тесты функции parse_product_details."""

    @pytest.mark.asyncio
    async def test_parse_product_details(self, sample_product_html: str) -> None:
        """Парсинг деталей товара."""
        with patch("db_handler.main.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_product_html

            result = await parse_product_details(
                "https://www.olx.uz/d/obyavlenie/test-ID123.html",
                usd_rate=12800,
                category="nedvizhimost",
            )

            assert result["category"] == "nedvizhimost"
            assert result["title"] == "Тестовый товар"
            assert result["price_uzs"] == 100000
            assert result["currency"] == "UZS"

    @pytest.mark.asyncio
    async def test_parse_product_details_usd_price(
        self, sample_product_html: str
    ) -> None:
        """Парсинг товара с ценой в USD."""
        html_with_usd = sample_product_html.replace("100 000 сум", "500 $")

        with patch("db_handler.main.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html_with_usd

            result = await parse_product_details(
                "https://www.olx.uz/d/obyavlenie/test.html",
                usd_rate=12800,
                category="transport",
            )

            assert result["currency"] == "USD"
            assert result["price_uzs"] == 500 * 12800

    @pytest.mark.asyncio
    async def test_parse_product_details_fetch_failed(self) -> None:
        """Когда загрузка страницы не удалась."""
        with patch("db_handler.main.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            result = await parse_product_details(
                "https://www.olx.uz/d/obyavlenie/test.html",
                usd_rate=12800,
                category="nedvizhimost",
            )

            assert result == {}


class TestParseProductsFromCategory:
    """Тесты функции parse_products_from_category."""

    @pytest.mark.asyncio
    async def test_parse_products_from_category(
        self, sample_category_html: str
    ) -> None:
        """Парсинг продуктов из категории."""
        with patch("db_handler.main.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_category_html

            result = await parse_products_from_category(
                "https://www.olx.uz/nedvizhimost/"
            )

            assert len(result) >= 2
            assert all(
                card.get("data-testid") == "l-card" for card in result
            )

    @pytest.mark.asyncio
    async def test_parse_products_from_category_fetch_failed(self) -> None:
        """Когда загрузка страницы не удалась."""
        with patch("db_handler.main.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            result = await parse_products_from_category(
                "https://www.olx.uz/nedvizhimost/"
            )

            assert result == []
