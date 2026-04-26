"""
Селекторы для парсинга OLX.UZ

Используем комбинированный подход с fallback:
1. data-testid (наиболее стабильные)
2. CSS классы (могут меняться)
3. Семантические селекторы (последний вариант)

Приоритет указан порядком в списке.
"""

# =============================================================================
# СТРАНИЦА КАТЕГОРИИ (список товаров)
# =============================================================================

CATEGORY_PAGE_SELECTORS = {
    # Контейнер списка товаров
    "product_container": [
        {"data-testid": "listing-grid"},
        {"class_": "css-j0t2x2"},
        {"data_nx_name": "ListContainer"},
    ],
    
    # Карточка товара
    "product_card": [
        {"data-testid": "l-card"},
        {"data-cy": "l-card"},
        {"class_": "css-1sw7q4x"},
    ],
    
    # Ссылка на товар (внутри карточки)
    "product_link": [
        {"tag": "a", "href_pattern": "/torg/"},
        {"tag": "a", "class_": "css-1tqlkj0"},
    ],
    
    # Заголовок товара
    "product_title": [
        {"data-testid": "ad-card-title"},
        {"class_": "css-u2ayx9"},
        {"tag": "h3"},
        {"tag": "h4"},
    ],
    
    # Цена товара
    "product_price": [
        {"data-testid": "ad-price"},
        {"class_": "css-blr5zl"},
        {"tag": "h3"},
        {"tag": "p"},
    ],
    
    # Локация и дата
    "product_location": [
        {"data-testid": "location-date"},
        {"class_": "css-3cz5o2"},
        {"tag": "p"},
    ],
    
    # Пагинация
    "pagination": [
        {"data-testid": "pagination-list"},
        {"tag": "ul", "class_": "css-1716elz"},
    ],
    
    # Изображение товара
    "product_image": [
        {"tag": "img"},
    ],
}

# =============================================================================
# СТРАНИЦА ТОВАРА (детальная информация)
# =============================================================================

PRODUCT_PAGE_SELECTORS = {
    # Заголовок товара
    "title": [
        {"data-testid": "heading"},
        {"tag": "h1"},
        {"class_": "css-xl2heb"},
        {"class_": "css-1au435n"},
    ],
    
    # Цена товара
    "price": [
        {"data-testid": "ad-price"},
        {"class_": "css-yauxmy"},
        {"tag": "h3"},
        {"tag": "h4"},
    ],
    
    # Дата публикации
    "date": [
        {"data-testid": "ad-posted-at"},
        {"class_": "css-1br3d2a"},
        {"tag": "span"},
    ],
    
    # Точная локация
    "precise_location": [
        {"data-testid": "address-map-link"},
        {"class_": "css-9pna1a"},
        {"tag": "p"},
    ],
    
    # Общая локация (район/город)
    "location": [
        {"data-testid": "location-district"},
        {"data-testid": "location-address"},
        {"class_": "css-3cz5o2"},
        {"tag": "p"},
    ],
    
    # Параметры товара (список характеристик)
    "parameters": [
        {"data-testid": "parameters-list"},
        {"class_": "css-6zsv65"},
        {"tag": "dl"},
        {"tag": "ul"},
    ],
    
    # Отдельный параметр (в списке параметров)
    "parameter_item": [
        {"class_": "css-13x8d99"},
        {"tag": "p"},
    ],
    
    # OLX ID объявления
    "olx_id": [
        {"data-testid": "advert-id"},
        {"class_": "css-ooacec"},
        {"tag": "span"},
    ],
    
    # Описание товара
    "description": [
        {"data-testid": "ad-description"},
        {"tag": "div", "class_": "css-1r93q13"},
    ],
    
    # Изображения товара
    "images": [
        {"data-testid": "ad-gallery"},
        {"tag": "img"},
    ],
}

# =============================================================================
# ОБЩИЕ СЕЛЕКТОРЫ
# =============================================================================

COMMON_SELECTORS = {
    # Контейнер категорий на главной странице
    "category_links": [
        {"data-testid": "home-categories-menu"},
        {"data-cy": "home-categories-menu"},
        {"class_": "css-1rwzo2t"},
    ],
    
    # Фильтры
    "filters": [
        {"data-testid": "listing-filters"},
        {"data-testid": "category-filter"},
    ],
}

# =============================================================================
# ФУНКЦИИ-ПОМОЩНИКИ
# =============================================================================

def get_selector_list(selectors_dict: dict, key: str) -> list:
    """Возвращает список селекторов для указанного ключа."""
    return selectors_dict.get(key, [])


def merge_selectors(*selectors_dicts) -> dict:
    """Объединяет несколько словарей селекторов."""
    result = {}
    for sd in selectors_dicts:
        for key, value in sd.items():
            if key not in result:
                result[key] = []
            result[key].extend(value if isinstance(value, list) else [value])
    return result
