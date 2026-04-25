"""
Тесты для модуля parser/selector_utils.py
"""
import pytest
from bs4 import BeautifulSoup
from parser.selector_utils import (
    find_with_fallback,
    get_text_or_default,
    log_selector_warning,
    validate_selectors,
)


class TestFindWithFallback:
    """Тесты функции find_with_fallback."""

    def test_find_by_data_testid(self, sample_soup: BeautifulSoup) -> None:
        """Поиск по data-testid атрибуту."""
        selectors = [{"data-testid": "l-card"}]
        result = find_with_fallback(sample_soup, selectors)
        assert result is not None
        assert result.name == "div"

    def test_find_by_class(self, sample_soup: BeautifulSoup) -> None:
        """Поиск по CSS классу."""
        selectors = [{"class_": "css-j0t2x2"}]
        result = find_with_fallback(sample_soup, selectors)
        assert result is not None
        assert result.name == "div"

    def test_find_by_tag(self, sample_soup: BeautifulSoup) -> None:
        """Поиск по тегу."""
        selectors = [{"tag": "ul"}]
        result = find_with_fallback(sample_soup, selectors)
        assert result is not None
        assert result.name == "ul"

    def test_find_with_fallback_chain(self, sample_soup: BeautifulSoup) -> None:
        """Поиск с цепочкой fallback."""
        selectors = [
            {"data-testid": "non-existent"},
            {"class_": "css-j0t2x2"},
        ]
        result = find_with_fallback(sample_soup, selectors)
        assert result is not None
        assert "css-j0t2x2" in result.get("class", [])

    def test_find_returns_none_when_not_found(self, sample_soup: BeautifulSoup) -> None:
        """Возврат None когда элемент не найден."""
        selectors = [{"data-testid": "non-existent"}]
        result = find_with_fallback(sample_soup, selectors, default=None)
        assert result is None

    def test_find_returns_default_when_not_found(self, sample_soup: BeautifulSoup) -> None:
        """Возврат значения по умолчанию."""
        selectors = [{"data-testid": "non-existent"}]
        default_value = "default"
        result = find_with_fallback(sample_soup, selectors, default=default_value)
        assert result == default_value

    def test_find_all_elements(self, sample_soup: BeautifulSoup) -> None:
        """Поиск всех элементов (find_all)."""
        selectors = [{"data-testid": "l-card"}]
        result = find_with_fallback(sample_soup, selectors, all=True)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_find_with_href_pattern(self, sample_soup: BeautifulSoup) -> None:
        """Поиск ссылки с паттерном href."""
        selectors = [{"tag": "a", "href_pattern": "/d/obyavlenie/"}]
        result = find_with_fallback(sample_soup, selectors)
        assert result is not None
        assert result.name == "a"
        assert "/d/obyavlenie/" in result.get("href", "")

    def test_find_nested_element(self, sample_soup: BeautifulSoup) -> None:
        """Поиск вложенного элемента."""
        container = find_with_fallback(
            sample_soup, [{"data-testid": "listing-grid"}]
        )
        assert container is not None

        card = find_with_fallback(container, [{"data-testid": "l-card"}])
        assert card is not None

        title = find_with_fallback(card, [{"data-testid": "ad-card-title"}])
        assert title is not None


class TestGetTextOrDefault:
    """Тесты функции get_text_or_default."""

    def test_get_text_from_element(self, sample_soup: BeautifulSoup) -> None:
        """Извлечение текста из элемента."""
        selectors = [{"data-testid": "ad-card-title"}]
        text = get_text_or_default(sample_soup, selectors, default="None")
        assert text == "Тестовый товар"

    def test_get_text_default_when_not_found(self, sample_soup: BeautifulSoup) -> None:
        """Возврат default когда элемент не найден."""
        selectors = [{"data-testid": "non-existent"}]
        text = get_text_or_default(sample_soup, selectors, default="Default")
        assert text == "Default"

    def test_get_text_strips_whitespace(self, sample_soup: BeautifulSoup) -> None:
        """Обрезка пробелов."""
        selectors = [{"data-testid": "ad-card-title"}]
        text = get_text_or_default(sample_soup, selectors, strip=True)
        assert text == text.strip()

    def test_get_text_first_from_list(self, sample_soup: BeautifulSoup) -> None:
        """Извлечение текста из первого элемента списка."""
        selectors = [{"data-testid": "ad-card-title"}]
        text = get_text_or_default(sample_soup, selectors, default="None", strip=True)
        assert text is not None
        assert text != "None"


class TestLogSelectorWarning:
    """Тесты функции log_selector_warning."""

    def test_log_warning_without_fallback(self, caplog: pytest.LogCaptureFixture) -> None:
        """Логирование предупреждения без fallback."""
        log_selector_warning("test_selector", "https://test.com", fallback_used=False)
        assert "Селектор 'test_selector' не найден" in caplog.text

    def test_log_warning_with_fallback(self, caplog: pytest.LogCaptureFixture) -> None:
        """Логирование предупреждения с fallback."""
        log_selector_warning("test_selector", "https://test.com", fallback_used=True)
        assert "использован fallback" in caplog.text


class TestValidateSelectors:
    """Тесты функции validate_selectors."""

    def test_validate_all_working_selectors(self, sample_soup: BeautifulSoup) -> None:
        """Валидация работающих селекторов."""
        selectors = {
            "card": [{"data-testid": "l-card"}],
            "title": [{"data-testid": "ad-card-title"}],
            "price": [{"data-testid": "ad-price"}],
        }
        result = validate_selectors(sample_soup, selectors)

        assert result["card"] is True
        assert result["title"] is True
        assert result["price"] is True

    def test_validate_mixed_selectors(self, sample_soup: BeautifulSoup) -> None:
        """Валидация смешанных селекторов."""
        selectors = {
            "working": [{"data-testid": "l-card"}],
            "not_working": [{"data-testid": "non-existent"}],
        }
        result = validate_selectors(sample_soup, selectors)

        assert result["working"] is True
        assert result["not_working"] is False

    def test_validate_empty_selectors(self, sample_soup: BeautifulSoup) -> None:
        """Валидация пустых селекторов."""
        result = validate_selectors(sample_soup, {})
        assert result == {}

    def test_validate_with_real_category_selectors(
        self, sample_soup: BeautifulSoup
    ) -> None:
        """Валидация реальных селекторов категории."""
        from parser.selectors import CATEGORY_PAGE_SELECTORS

        result = validate_selectors(sample_soup, CATEGORY_PAGE_SELECTORS)

        # Основные селекторы должны работать
        assert result.get("product_card") is True
        assert result.get("product_title") is True
        assert result.get("product_price") is True
        assert result.get("pagination") is True
