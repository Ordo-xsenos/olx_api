"""
Скрипт для исследования HTML-структуры olx.uz
и поиска стабильных селекторов (data-атрибуты, семантические теги).
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

MAIN_URL = "https://www.olx.uz"


async def fetch_page(url: str) -> str | None:
    """Скачивает страницу."""
    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; olx-scraper/2.0)"},
        follow_redirects=True
    ) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"Ошибка загрузки {url}: {e}")
            return None


def find_data_attributes(soup: BeautifulSoup, tag_name: str = None) -> dict:
    """Ищет все data-* атрибуты на странице."""
    result = {}
    
    for tag in soup.find_all(True):  # Все теги
        if tag_name and tag.name != tag_name:
            continue
            
        data_attrs = {k: v for k, v in tag.attrs.items() if k.startswith("data-")}
        if data_attrs:
            tag_key = f"<{tag.name}>"
            if tag.get("class"):
                tag_key = f"<{tag.name} class='{tag.get('class')}'>"
            
            if tag_key not in result:
                result[tag_key] = []
            result[tag_key].append(data_attrs)
    
    return result


def analyze_category_page(soup: BeautifulSoup) -> dict:
    """Анализирует страницу категории."""
    analysis = {
        "category_links": [],
        "product_containers": [],
        "product_cards": [],
        "pagination": None,
    }
    
    # 1. Ищем ссылки на категории
    print("\n=== КАТЕГОРИИ ===")
    # Пробуем разные подходы
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True)[:50]
        
        # Ищем категории по паттернам в URL
        if any(x in href for x in ["/nedvizhimost/", "/transport/", "/rabota/"]):
            analysis["category_links"].append({
                "href": href,
                "text": text,
                "tag": str(link)[:200],
                "data_attrs": {k: v for k, v in link.attrs.items() if k.startswith("data-")},
                "parent": str(link.parent)[:150] if link.parent else None,
            })
            print(f"  Категория: {text} -> {href}")
    
    # 2. Ищем контейнеры товаров
    print("\n=== КОНТЕЙНЕРЫ ТОВАРОВ ===")
    # Ищем по разным признакам
    containers = soup.find_all(["div", "section", "main"])
    for container in containers[:50]:  # Ограничим вывод
        classes = container.get("class", [])
        data_attrs = {k: v for k, v in container.attrs.items() if k.startswith("data-")}
        
        # Проверяем, есть ли внутри ссылки на товары
        links = container.find_all("a", href=True)
        product_links = [l for l in links if "/torg/" in l.get("href", "")]
        
        if product_links or data_attrs:
            info = {
                "tag": container.name,
                "classes": classes,
                "data_attrs": data_attrs,
                "product_links_count": len(product_links),
            }
            analysis["product_containers"].append(info)
            if data_attrs or len(product_links) > 3:
                print(f"  Контейнер: <{container.name}> classes={classes}")
                print(f"    data-attrs: {data_attrs}")
                print(f"    товаров внутри: {len(product_links)}")
    
    # 3. Ищем карточки товаров
    print("\n=== КАРТОЧКИ ТОВАРОВ ===")
    # Ищем по ссылкам с /torg/
    for link in soup.find_all("a", href=lambda x: x and "/torg/" in x):
        card = link.parent
        while card and card.name != "body":
            classes = card.get("class", [])
            data_attrs = {k: v for k, v in card.attrs.items() if k.startswith("data-")}
            
            # Проверяем, похож ли элемент на карточку
            if classes or data_attrs:
                # Ищем внутри цену и заголовок
                price = card.find(["h3", "p"], string=lambda x: x and any(c in x.lower() for c in ["$", "сум", "uzs"]))
                title = card.find(["h3", "h4", "p"])
                
                if price or title or data_attrs:
                    card_info = {
                        "tag": card.name,
                        "classes": classes,
                        "data_attrs": data_attrs,
                        "has_price": price is not None,
                        "has_title": title is not None,
                    }
                    if card_info not in analysis["product_cards"]:
                        analysis["product_cards"].append(card_info)
                        if data_attrs or (classes and len(classes) > 0):
                            print(f"  Карточка: <{card.name}> classes={classes}")
                            print(f"    data-attrs: {data_attrs}")
                            print(f"    есть цена: {price is not None}, заголовок: {title is not None}")
                    break
            card = card.parent
    
    # 4. Пагинация
    print("\n=== ПАГИНАЦИЯ ===")
    pagination = soup.find(["ul", "nav"], {"data-testid": lambda x: x and "pagination" in x.lower()})
    if pagination:
        analysis["pagination"] = {
            "tag": pagination.name,
            "data_attrs": {k: v for k, v in pagination.attrs.items() if k.startswith("data-")},
        }
        print(f"  Найдено: <{pagination.name}> {pagination.get('data-testid', '')}")
    else:
        # Ищем альтернативы
        for nav in soup.find_all(["ul", "nav"]):
            links = nav.find_all("a")
            if len(links) > 1 and any("page" in l.get_text().lower() for l in links):
                print(f"  Альтернатива: <{nav.name}> с {len(links)} ссылками")
                analysis["pagination"] = {"tag": nav.name, "links_count": len(links)}
    
    return analysis


def analyze_product_page(soup: BeautifulSoup) -> dict:
    """Анализирует страницу товара."""
    analysis = {
        "title": [],
        "price": [],
        "location": [],
        "description": [],
        "parameters": [],
        "images": [],
    }
    
    print("\n=== ЗАГОЛОВОК ===")
    # Ищем заголовки разных уровней
    for tag in ["h1", "h2", "h3", "h4"]:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            if text and len(text) > 5:
                data_attrs = {k: v for k, v in el.attrs.items() if k.startswith("data-")}
                info = {
                    "tag": tag,
                    "classes": el.get("class", []),
                    "text_preview": text[:50],
                    "data_attrs": data_attrs,
                }
                analysis["title"].append(info)
                if data_attrs or len(text) < 100:  # Вероятно заголовок
                    print(f"  <{tag}> classes={el.get('class', [])}")
                    print(f"    text: {text[:50]}...")
                    print(f"    data-attrs: {data_attrs}")
    
    print("\n=== ЦЕНА ===")
    # Ищем цену
    for tag in ["h3", "h4", "p", "span"]:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            # Проверяем, похоже ли на цену
            if text and any(x in text for x in ["$", "сум", "сум", "Uzbekistan som", "договор"]):
                data_attrs = {k: v for k, v in el.attrs.items() if k.startswith("data-")}
                info = {
                    "tag": tag,
                    "classes": el.get("class", []),
                    "text_preview": text[:50],
                    "data_attrs": data_attrs,
                }
                analysis["price"].append(info)
                print(f"  <{tag}> classes={el.get('class', [])}")
                print(f"    text: {text}")
                print(f"    data-attrs: {data_attrs}")
    
    print("\n=== ЛОКАЦИЯ ===")
    # Ищем локацию
    for el in soup.find_all(["p", "span", "div"], string=lambda x: x and any(
        city in x.lower() for city in ["ташкент", "самарканд", "бухара", "наманган", "андижан"]
    )):
        data_attrs = {k: v for k, v in el.parent.attrs.items() if k.startswith("data-")}
        info = {
            "tag": el.parent.name,
            "classes": el.parent.get("class", []),
            "text_preview": str(el)[:100],
            "data_attrs": data_attrs,
        }
        analysis["location"].append(info)
        print(f"  <{el.parent.name}> classes={el.parent.get('class', [])}")
        print(f"    text: {str(el)[:100]}")
        print(f"    data-attrs: {data_attrs}")
    
    print("\n=== ПАРАМЕТРЫ ===")
    # Ищем списки параметров
    for tag in ["ul", "dl", "div"]:
        for el in soup.find_all(tag):
            data_attrs = {k: v for k, v in el.attrs.items() if k.startswith("data-")}
            # Проверяем, есть ли внутри пары ключ-значение
            items = el.find_all(["li", "dt", "dd", "p"])
            if data_attrs or (len(items) > 2 and len(items) < 20):
                info = {
                    "tag": tag,
                    "classes": el.get("class", []),
                    "data_attrs": data_attrs,
                    "items_count": len(items),
                }
                if info not in analysis["parameters"]:
                    analysis["parameters"].append(info)
                    if data_attrs:
                        print(f"  <{tag}> classes={el.get('class', [])}")
                        print(f"    data-attrs: {data_attrs}")
                        print(f"    элементов: {len(items)}")
    
    return analysis


async def main():
    print("=" * 60)
    print("ИССЛЕДОВАНИЕ СТРУКТУРЫ OLX.UZ")
    print("=" * 60)
    
    # 1. Главная страница (список категорий)
    print("\n\n>>> ГЛАВНАЯ СТРАНИЦА")
    main_html = await fetch_page(MAIN_URL)
    if main_html:
        main_soup = BeautifulSoup(main_html, "html.parser")
        with open("research_main_page.html", "w", encoding="utf-8") as f:
            f.write(main_html)
        print("HTML сохранён в research_main_page.html")
        analyze_category_page(main_soup)
    
    # 2. Страница категории
    print("\n\n>>> СТРАНИЦА КАТЕГОРИИ (Недвижимость)")
    category_url = urljoin(MAIN_URL, "/nedvizhimost/")
    category_html = await fetch_page(category_url)
    if category_html:
        category_soup = BeautifulSoup(category_html, "html.parser")
        with open("research_category_page.html", "w", encoding="utf-8") as f:
            f.write(category_html)
        print("HTML сохранён в research_category_page.html")
        category_analysis = analyze_category_page(category_soup)
        
        # Экспорт результатов в JSON
        with open("research_category_selectors.json", "w", encoding="utf-8") as f:
            json.dump(category_analysis, f, ensure_ascii=False, indent=2)
        print("\nРезультаты сохранены в research_category_selectors.json")
    
    # 3. Страница товара (если нашли ссылку)
    if category_analysis.get("product_cards"):
        # Ищем ссылку на товар
        product_link = None
        for link in category_soup.find_all("a", href=lambda x: x and "/torg/" in x):
            product_link = urljoin(MAIN_URL, link.get("href"))
            break
        
        if product_link:
            print(f"\n\n>>> СТРАНИЦА ТОВАРА: {product_link}")
            product_html = await fetch_page(product_link)
            if product_html:
                product_soup = BeautifulSoup(product_html, "html.parser")
                with open("research_product_page.html", "w", encoding="utf-8") as f:
                    f.write(product_html)
                print("HTML сохранён в research_product_page.html")
                analyze_product_page(product_soup)
    
    print("\n" + "=" * 60)
    print("ИССЛЕДОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
