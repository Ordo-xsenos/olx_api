"""
Утилиты для поиска элементов в HTML с использованием fallback-селекторов.

Основная идея: пробуем несколько селекторов по порядку, пока не найдём элемент.
Это делает парсер устойчивым к изменениям вёрстки на сайте.
"""
import logging
from typing import Any, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def find_with_fallback(
    parent: BeautifulSoup | Tag,
    selectors: list[dict],
    default: Any = None,
    all: bool = False,
    selector_name: str = "",
) -> Tag | list[Tag] | None:
    """
    Ищет элемент(ы) по списку селекторов с fallback.
    
    Args:
        parent: BeautifulSoup или Tag для поиска
        selectors: Список селекторов для попытки. Каждый селектор — dict с параметрами:
            - data-testid: поиск по data-testid атрибуту
            - data-cy: поиск по data-cy атрибуту
            - class_: поиск по CSS классу
            - tag: тег элемента (a, div, p, etc.)
            - href_pattern: паттерн для href (для ссылок)
            - data_nx_name: поиск по data-nx-name атрибуту
        default: Значение по умолчанию если ничего не найдено
        all: Если True, возвращает все найденные элементы (find_all)
        selector_name: Имя селектора для логирования (опционально)
    
    Returns:
        Tag или list[Tag] если найдено, иначе default
    """
    for i, selector in enumerate(selectors):
        try:
            result = _apply_selector(parent, selector, all)
            
            if result:
                if selector_name:
                    logger.debug(
                        "Селектор #%d сработал для '%s': %s",
                        i + 1, selector_name, selector
                    )
                return result
                
        except Exception as e:
            logger.debug(
                "Селектор #%d ошибся для '%s': %s — %s",
                i + 1, selector_name, selector, e
            )
            continue
    
    # Ничего не найдено
    if selector_name:
        logger.debug("Ни один селектор не сработал для '%s'", selector_name)
    return default


def _apply_selector(
    parent: BeautifulSoup | Tag,
    selector: dict,
    all: bool = False,
) -> Tag | list[Tag] | None:
    """Применяет один селектор к родителю."""
    find_method = parent.find_all if all else parent.find
    
    # Поиск по data-testid
    if "data-testid" in selector:
        result = find_method(attrs={"data-testid": selector["data-testid"]})
        if result:
            return result
    
    # Поиск по data-cy
    if "data-cy" in selector:
        result = find_method(attrs={"data-cy": selector["data-cy"]})
        if result:
            return result
    
    # Поиск по data-nx-name
    if "data_nx_name" in selector:
        result = find_method(attrs={"data-nx-name": selector["data_nx_name"]})
        if result:
            return result
    
    # Поиск по CSS классу
    if "class_" in selector:
        kwargs = {"class_": selector["class_"]}
        if "tag" in selector:
            result = find_method(selector["tag"], **kwargs)
        else:
            result = find_method(**kwargs)
        if result:
            return result
    
    # Поиск по тегу с паттерном href
    if "href_pattern" in selector:
        tag = selector.get("tag", "a")
        pattern = selector["href_pattern"]
        
        def href_match(href: str) -> bool:
            return href and pattern in href
        
        result = find_method(tag, href=href_match)
        if result:
            return result
        
        # Если не нашли по паттерну, пробуем просто тег
        if "tag" in selector:
            result = find_method(tag)
            if result:
                return result
    
    # Поиск только по тегу
    if "tag" in selector and len(selector) == 1:
        result = find_method(selector["tag"])
        if result:
            return result
    
    return None


def get_text_or_default(
    parent: BeautifulSoup | Tag,
    selectors: list[dict],
    default: str = "None",
    selector_name: str = "",
    strip: bool = True,
) -> str:
    """
    Извлекает текст из элемента, найденного через fallback-селекторы.
    
    Args:
        parent: BeautifulSoup или Tag для поиска
        selectors: Список селекторов для попытки
        default: Значение по умолчанию если ничего не найдено
        selector_name: Имя селектора для логирования
        strip: Обрезать ли пробелы
    
    Returns:
        Текст элемента или default
    """
    result = find_with_fallback(
        parent, selectors, default=None,
        selector_name=selector_name
    )
    
    if result is None:
        return default
    
    # Если это список элементов, берём первый
    if isinstance(result, list):
        if not result:
            return default
        result = result[0]
    
    # Извлекаем текст
    text = result.get_text()
    if strip:
        text = text.strip()
    
    return text if text else default


def log_selector_warning(selector_name: str, url: str, fallback_used: bool = False) -> None:
    """
    Логирует предупреждение о проблемах с селектором.
    
    Args:
        selector_name: Имя селектора
        url: URL страницы где произошла проблема
        fallback_used: Был ли использован fallback
    """
    if fallback_used:
        logger.warning(
            "Селектор '%s' не найден, использован fallback. URL: %s",
            selector_name, url
        )
    else:
        logger.warning(
            "Селектор '%s' не найден. URL: %s",
            selector_name, url
        )


def validate_selectors(soup: BeautifulSoup, selectors: dict) -> dict[str, bool]:
    """
    Проверяет, какие селекторы работают на данной странице.
    
    Args:
        soup: BeautifulSoup страницы
        selectors: Словарь селекторов
    
    Returns:
        Dict {selector_name: True/False}
    """
    results = {}
    for name, selector_list in selectors.items():
        result = find_with_fallback(soup, selector_list, default=None)
        results[name] = result is not None
    return results
