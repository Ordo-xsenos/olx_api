"""
Тесты для модуля parser/selectors.py
"""
import pytest
from parser.selectors import (
    CATEGORY_PAGE_SELECTORS,
    PRODUCT_PAGE_SELECTORS,
    COMMON_SELECTORS,
    get_selector_list,
    merge_selectors,
)


class TestCategoryPageSelectors:
    """Тесты селекторов страницы категории."""

    def test_product_container_exists(self) -> None:
        """Проверка наличия селектора контейнера товаров."""
        assert "product_container" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["product_container"], list)
        assert len(CATEGORY_PAGE_SELECTORS["product_container"]) > 0

    def test_product_card_exists(self) -> None:
        """Проверка наличия селектора карточки товара."""
        assert "product_card" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["product_card"], list)
        assert len(CATEGORY_PAGE_SELECTORS["product_card"]) > 0

    def test_product_title_exists(self) -> None:
        """Проверка наличия селектора заголовка."""
        assert "product_title" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["product_title"], list)

    def test_product_price_exists(self) -> None:
        """Проверка наличия селектора цены."""
        assert "product_price" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["product_price"], list)

    def test_product_location_exists(self) -> None:
        """Проверка наличия селектора локации."""
        assert "product_location" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["product_location"], list)

    def test_pagination_exists(self) -> None:
        """Проверка наличия селектора пагинации."""
        assert "pagination" in CATEGORY_PAGE_SELECTORS
        assert isinstance(CATEGORY_PAGE_SELECTORS["pagination"], list)

    def test_selector_has_data_testid(self) -> None:
        """Проверка что селекторы содержат data-testid."""
        # Некоторые ключи могут не иметь data-testid (это нормально)
        keys_with_data_testid = []
        for name, selectors in CATEGORY_PAGE_SELECTORS.items():
            has_data_testid = any(
                "data-testid" in s for s in selectors if isinstance(s, dict)
            )
            if has_data_testid:
                keys_with_data_testid.append(name)
        
        # Проверяем что хотя бы некоторые селекторы имеют data-testid
        assert len(keys_with_data_testid) > 0, "Ни один селектор не имеет data-testid"


class TestProductPageSelectors:
    """Тесты селекторов страницы товара."""

    def test_title_exists(self) -> None:
        """Проверка наличия селектора заголовка."""
        assert "title" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["title"], list)

    def test_price_exists(self) -> None:
        """Проверка наличия селектора цены."""
        assert "price" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["price"], list)

    def test_date_exists(self) -> None:
        """Проверка наличия селектора даты."""
        assert "date" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["date"], list)

    def test_location_exists(self) -> None:
        """Проверка наличия селектора локации."""
        assert "location" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["location"], list)

    def test_parameters_exists(self) -> None:
        """Проверка наличия селектора параметров."""
        assert "parameters" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["parameters"], list)

    def test_olx_id_exists(self) -> None:
        """Проверка наличия селектора OLX ID."""
        assert "olx_id" in PRODUCT_PAGE_SELECTORS
        assert isinstance(PRODUCT_PAGE_SELECTORS["olx_id"], list)


class TestCommonSelectors:
    """Тесты общих селекторов."""

    def test_category_links_exists(self) -> None:
        """Проверка наличия селектора ссылок категорий."""
        assert "category_links" in COMMON_SELECTORS
        assert isinstance(COMMON_SELECTORS["category_links"], list)

    def test_filters_exists(self) -> None:
        """Проверка наличия селектора фильтров."""
        assert "filters" in COMMON_SELECTORS
        assert isinstance(COMMON_SELECTORS["filters"], list)


class TestGetSelectorList:
    """Тесты функции get_selector_list."""

    def test_get_existing_selector(self) -> None:
        """Получение существующего селектора."""
        result = get_selector_list(CATEGORY_PAGE_SELECTORS, "product_card")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_non_existing_selector(self) -> None:
        """Получение несуществующего селектора."""
        result = get_selector_list(CATEGORY_PAGE_SELECTORS, "non_existing")
        assert result == []


class TestMergeSelectors:
    """Тесты функции merge_selectors."""

    def test_merge_two_dicts(self) -> None:
        """Объединение двух словарей селекторов."""
        dict1 = {"test1": [{"data-testid": "test1"}]}
        dict2 = {"test2": [{"data-testid": "test2"}]}

        result = merge_selectors(dict1, dict2)

        assert "test1" in result
        assert "test2" in result
        assert len(result["test1"]) == 1
        assert len(result["test2"]) == 1

    def test_merge_overlapping_dicts(self) -> None:
        """Объединение словарей с одинаковыми ключами."""
        dict1 = {"test": [{"data-testid": "test1"}]}
        dict2 = {"test": [{"data-testid": "test2"}]}

        result = merge_selectors(dict1, dict2)

        assert "test" in result
        assert len(result["test"]) == 2

    def test_merge_empty_dicts(self) -> None:
        """Объединение пустых словарей."""
        result = merge_selectors({}, {})
        assert result == {}

    def test_merge_multiple_dicts(self) -> None:
        """Объединение нескольких словарей."""
        dict1 = {"a": [{"data-testid": "a1"}]}
        dict2 = {"b": [{"data-testid": "b1"}]}
        dict3 = {"c": [{"data-testid": "c1"}]}

        result = merge_selectors(dict1, dict2, dict3)

        assert len(result) == 3
        assert all(key in result for key in ["a", "b", "c"])
