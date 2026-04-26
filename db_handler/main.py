import bs4
import json
import re
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
import logging
import httpx
import asyncio
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from config import settings
from db_handler.http_client import get_http_client
from parser.selectors import CATEGORY_PAGE_SELECTORS, PRODUCT_PAGE_SELECTORS
from parser.selector_utils import find_with_fallback, get_text_or_default as get_text_fallback


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Для отладки селекторов можно установить DEBUG уровень
# logger.setLevel(logging.DEBUG)

main_url = "https://www.olx.uz"
# Ограничиваем количество одновременных запросов (чтобы не забанили)
MAX_CONCURRENT_REQUESTS = settings.max_concurrent_requests
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def normalize_listing_url(raw_url: str) -> str:
	"""Возвращает канонический URL объявления без параметров запроса и фрагментов."""
	parts = urlsplit(raw_url)
	path = parts.path.rstrip("/") or parts.path
	return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


async def fetch(url: str) -> str | None:
	"""Асинхронное скачивание страницы с ограничением через семафор."""
	async with semaphore:
		try:
			client = get_http_client()
			resp = await client.get(url)
			resp.raise_for_status()
			# Короткая пауза между запросами внутри семафора
			await asyncio.sleep(0.1)
			return resp.text
		except httpx.HTTPError as e:
			logger.error("Ошибка HTTP запроса %s: %s", url, e)
			return None
		except Exception as e:
			if isinstance(e, (KeyboardInterrupt, SystemExit)):
				raise
			logger.error("Неожиданная ошибка при запросе %s: %s", url, e, exc_info=True)
			return None


def get_text_or_default(parent: BeautifulSoup | bs4.Tag, tag, cls: str, default="None"):
    """
    Безопасно извлекает текст из HTML-элемента.
    Устаревшая функция, оставлена для обратной совместимости.
    Рекомендуется использовать get_text_fallback() с селекторами.
    """
    # Если parent пустой (None, пустая строка и т.п.) — возвращаем default
    if not parent:
        return default

    try:
        from bs4 import element as _bs4_element
    except Exception:
        _bs4_element = None

    # Если parent — строка или NavigableString, вернём её содержимое
    if isinstance(parent, str) or (
            _bs4_element is not None and isinstance(parent, _bs4_element.NavigableString)
    ):
        text = parent.strip()
        return text if text else default

    # Если у parent есть метод find (как у Tag/BeautifulSoup) — используем его
    if hasattr(parent, "find") and callable(getattr(parent, "find")):
        try:
            el = parent.find(tag, class_=cls)
        except TypeError:
            # На всякий случай — если find неожиданно не поддерживает class_
            try:
                el = parent.find(tag)
            except Exception:
                return default

            return el.get_text(strip=True) if el else default

        return el.get_text(strip=True) if el else default

    # В общем случае возвращаем default
    return default


async def parse_category_urls(url : str) -> list[str]:
	category_urls = []

	text = await fetch(url)
	if not text:
		return category_urls

	soup = bs4.BeautifulSoup(text, "html.parser")
	category = soup.find_all("div", class_="css-1gw3rcq")
	if not category:
		return category_urls
	link_tag = category[0].find_all("a")
	for link in link_tag:
		href = link.get("href")
		if not href:
			continue
		# используем urljoin для корректной сборки URL
		if link_tag[-1] != link:
			category_urls.append(urljoin(url, href))
		else:
			category_urls.append(
				href if href.startswith("http") else urljoin(url, href)
			)
	return category_urls


def get_total_pages(soup : bs4.BeautifulSoup) -> int:
	try:
		# Ищем контейнер с пагинацией
		pagination_container = soup.find(
			"ul", {"data-testid": "pagination-list"}
		)
		if not pagination_container:
			logger.info("Пагинация не найдена, считаем, что страница одна.")
			return 1

		#Находим все ссылки на страницы
		links = pagination_container.find_all("a")
		if not links:
			return 1

		#берем последний элемент
		last_page_text = links[-1].get_text(strip=True)

		# Если в конце стоит стрелочка ">", берем предпоследний элемент
		if not last_page_text.isdigit():
			last_page_text = links[-2].get_text(strip=True)

		total_pages = int(last_page_text)
		logger.info("Найдено страниц для парсинга: %s", total_pages)
		return total_pages

	except Exception as e:
		logger.error("Ошибка при определении количества страниц: %s", e)
		return 1


async def parse_products_from_category(category_url: str) -> list[bs4.element.Tag]:
    """
    Парсит товары из категории с использованием fallback-селекторов.
    
    Использует приоритет:
    1. data-testid="listing-grid" для контейнера
    2. data-testid="l-card" для карточек товаров
    3. CSS классы как fallback
    """
    all_items = []  # Список для хранения HTML-блоков

    # Загружаем первую страницу для анализа
    text = await fetch(category_url)
    if not text:
        logger.warning("Не удалось загрузить начальную страницу: %s", category_url)
        return []

    soup = bs4.BeautifulSoup(text, "html.parser")
    total_pages = get_total_pages(soup)

    # Проходим по всем страницам
    for page_num in range(1, total_pages + 1):
        logger.info("Сбор товаров: страница %s из %s", page_num, total_pages)

        if page_num > 1:
            if "?" in category_url:
                current_url = f"{category_url}&page={page_num}"
            else:
                current_url = f"{category_url.rstrip('/')}/?page={page_num}"
            page_text = await fetch(current_url)
            if not page_text:
                continue
            soup = bs4.BeautifulSoup(page_text, "html.parser")

        # Находим контейнер с товарами (используем fallback-селекторы)
        container = find_with_fallback(
            soup,
            CATEGORY_PAGE_SELECTORS["product_container"],
            default=None,
            selector_name="product_container"
        )
        
        if container:
            # Находим все карточки товаров
            items = find_with_fallback(
                container,
                CATEGORY_PAGE_SELECTORS["product_card"],
                default=[],
                all=True,
                selector_name="product_card"
            )
            all_items.extend(items)
        else:
            logger.warning(
                "Контейнер товаров не найден на %s. Пробуем альтернативу...",
                category_url
            )
            # Альтернатива: ищем все карточки напрямую
            items = find_with_fallback(
                soup,
                CATEGORY_PAGE_SELECTORS["product_card"],
                default=[],
                all=True,
                selector_name="product_card"
            )
            all_items.extend(items)

    logger.info("Найдено товаров: %s", len(all_items))
    return all_items


def extract_products_links(products: list[bs4.element.Tag]) -> list[str]:
    """
    Извлекает ссылки на товары из карточек с использованием fallback-селекторов.
    """
    links = []

    for product in products:
        # Ищем ссылку с приоритетом: href содержит /torg/ или /d/obyavlenie/
        a = find_with_fallback(
            product,
            CATEGORY_PAGE_SELECTORS["product_link"],
            default=None,
            selector_name="product_link"
        )
        
        if not a:
            # Альтернатива: просто первая ссылка в карточке
            a = product.find("a", href=True)
        
        if not a:
            continue

        href = a.get("href")
        if not href:
            continue
            
        if not href.startswith("http"):
            href = urljoin(main_url, href)

        links.append(href)

    return links


async def parse_product_details(ad_url, usd_rate: int, category: str) -> dict:
    """
    Асинхронная версия парсинга деталей объявления.
    Использует fallback-селекторы для устойчивости к изменениям вёрстки.
    """
    text = await fetch(ad_url)
    if not text:
        return {}
    soup = bs4.BeautifulSoup(text, "html.parser")

    details = {}

    # Категория
    if "nedvizhimost" in ad_url:
        details["category"] = "nedvizhimost"
    else:
        details["category"] = category.removeprefix("https://www.olx.uz/").strip("/")
    
    # Заголовок — используем селекторы с fallback
    details["title"] = get_text_fallback(
        soup,
        PRODUCT_PAGE_SELECTORS["title"],
        default="None",
        selector_name="title"
    )
    
    # Дата публикации
    details["date"] = get_text_fallback(
        soup,
        PRODUCT_PAGE_SELECTORS["date"],
        default="None",
        selector_name="date"
    )
    # Fallback для даты
    if details["date"] == "None":
        details["date"] = get_text_fallback(
            soup,
            [{"class_": "css-1br3d2a"}, {"tag": "span"}],
            default="None",
            selector_name="date_fallback"
        )
    
    #--- Логика ЦЕН ---
    raw_price_value = get_text_fallback(
        soup,
        PRODUCT_PAGE_SELECTORS["price"],
        default="None",
        selector_name="price"
    )
    source_value, currency = parse_price_value(raw_price_value)

    details["original_price"] = source_value  # Сохраняем то, что было
    details["currency"] = currency
    
    # Конвертация в сумы для сортировки в БД
    if source_value is None:
        details["price_uzs"] = None  # Цена не указана
    elif currency == "UZS":
        details["price_uzs"] = source_value
    elif currency == "USD":
        # Умножаем на курс доллара
        details["price_uzs"] = source_value * usd_rate
    else:
        details["price_uzs"] = 0

    # Превращаем в float или int только в самом конце для JSON и БД
    if isinstance(details["price_uzs"], Decimal):
        details["price_uzs"] = int(details["price_uzs"])

    #--- Логика ЛОКАЦИИ ---
    # Ищем контейнер локации
    location_div = find_with_fallback(
        soup,
        [{"data-testid": "location-address"}, {"class_": "css-1deibjd"}],
        default=soup,
        selector_name="location_div"
    )
    
    details["precise_location"] = get_text_fallback(
        location_div,
        PRODUCT_PAGE_SELECTORS["precise_location"],
        default="None",
        selector_name="precise_location"
    )
    details["location"] = get_text_fallback(
        location_div,
        PRODUCT_PAGE_SELECTORS["location"],
        default="None",
        selector_name="location"
    )
    
    # Параметры товара
    parameters_div = find_with_fallback(
        soup,
        PRODUCT_PAGE_SELECTORS["parameters"],
        default=None,
        selector_name="parameters"
    )
    parameters_list = []
    if parameters_div:
        parameters_containers = find_with_fallback(
            parameters_div,
            PRODUCT_PAGE_SELECTORS["parameter_item"],
            default=[],
            all=True,
            selector_name="parameter_item"
        )
        for parameter in parameters_containers:
            if hasattr(parameter, 'get_text'):
                parameter = parameter.get_text()
            parameters_list.append(parameter)
    details["parameters"] = parameters_list
    
    # OLX ID
    olx_id = get_text_fallback(
        soup,
        PRODUCT_PAGE_SELECTORS["olx_id"],
        default="None",
        selector_name="olx_id"
    )
    details["olx_id"] = olx_id if olx_id and olx_id != "None" else None
    
    # URL (нормализованный)
    details["url"] = normalize_listing_url(ad_url)

    return details


def parse_price_value(text: str) -> tuple[int | None, str]:
	"""Извлекает числовое значение цены и валюту из текстовой строки."""
	if not text:
		return None, "UNKNOWN"

	s = text.lower().replace("\u00a0", " ").strip()

	if "договор" in s or "торг" in s or "по договорённости" in s:
		return None, "NEGOTIABLE"

	m = re.search(r"(\d{1,3}(?:[\s]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)", s)
	if not m:
		return None, "UNKNOWN"

	num_str = m.group(1).replace(" ", "").replace(",", ".")
	try:
		if "." in num_str:
			value = float(num_str)
		else:
			value = int(num_str)
	except InvalidOperation:
		return None, "UNKNOWN"

	if "$" in s or "usd" in s or "y.e" in s or "у.е" in s:
		currency = "USD"
	else:
		currency = "UZS"

	return value, currency


async def get_current_usd_rate() -> int:
	"""Получает курс USD/UZS один раз."""
	url = "https://v6.exchangerate-api.com/v6/d8aad1c4d700d6cd1dc68e14/latest/USD"
	try:


		# Используем твой fetch, который возвращает строку
		text_response = await fetch(url)
		if not text_response:
			logger.error("Пустой ответ от API курсов")
			return int("12800")  # Резервный курс, если API недоступен

		data = json.loads(text_response)  # Парсим строку в JSON

		if data.get("result") == "success":
			rate = data["conversion_rates"].get("UZS")
			logger.info(f"Актуальный курс доллара: {rate}")
			return int(rate)
		else:
			logger.error("Сервис курсов вернул ошибку")
			return int("12800")

	except Exception as e:
		logger.error(f"Ошибка получения курса: {e}")
		return int("12800") # Возвращаем примерный курс при ошибке


class Query:
	def __init__(self):
		self.filters = []
		self._results = []

	def where(self, rule):
		self.filters.append(rule)
		return self

	def execute(self, items):
		self._results = []
		for item in items:
			if all(f(item) for f in self.filters):
				self._results.append(item)
				yield item

	def to_json(self, path):
		with open(path, "w", encoding="utf-8") as f:
			json.dump(self._results, f, ensure_ascii=False, indent=2)


class Filters:
	def __init__(self):
		self.rules = []

	def price_below(self, max_price_uzs):
		def _f(item):
			# Поддерживаем и сырые, и нормализованные данные
			value = item.get("price") or item.get("original_price")
			currency = item.get("currency")
			if value is None:
				return False

			# Если это нормализованная цена в сумах
			if "price_uzs" in item and item["price_uzs"] is not None:
				return item["price_uzs"] <= max_price_uzs * 12800 # условно в сумы если max_price в у.е.
				# Или если max_price_uzs уже в сумах:
				# return item["price_uzs"] <= max_price_uzs

			if currency == "USD":
				value *= 12800  # примерный курс

			return value <= max_price_uzs

		self.rules.append(_f)
		return self

	def city(self, city):
		def _f(item):
			location = item.get("location")
			if not location or not isinstance(location, str):
				return False
			return city.lower() in location.lower()
		self.rules.append(_f)
		return self

	def keyword(self, word):
		def _f(item):
			title = item.get("title")
			if not title or not isinstance(title, str):
				return False
			return word.lower() in title.lower()
		self.rules.append(_f)
		return self

	def date(self, text):
		def _f(item):
			date_val = item.get("date")
			if not date_val or not isinstance(date_val, str):
				return False
			return text.lower() in date_val.lower()
		self.rules.append(_f)
		return self

	def match(self, item):
		return all(rule(item) for rule in self.rules)


filters = (
	Filters()
	#.price_below(1000_000)
	#.city("Ташкент")
	#.date("Сегодня")
)

results = []


def validate_selectors_on_page(page_type: str, html_content: str) -> dict[str, bool]:
    """
    Проверяет, какие селекторы работают на данной странице.
    
    Args:
        page_type: "category" или "product"
        html_content: HTML содержимое страницы
    
    Returns:
        Dict {selector_name: True/False}
    """
    from parser.selector_utils import validate_selectors
    
    soup = bs4.BeautifulSoup(html_content, "html.parser")
    
    if page_type == "category":
        return validate_selectors(soup, CATEGORY_PAGE_SELECTORS)
    elif page_type == "product":
        return validate_selectors(soup, PRODUCT_PAGE_SELECTORS)
    else:
        raise ValueError(f"Неизвестный тип страницы: {page_type}")


async def run_parsing():
	categories = await parse_category_urls(main_url)
	url_dict = {urlparse(url).path: url for url in categories}
	user_input = input("Введите путь категории для парсинга (например, /nedvizhimost/): ").strip()
	if user_input not in url_dict:
		logger.warning("Неверный путь категории: %s", user_input)
		return
	target_category = url_dict[user_input]
	logger.info("Начинаем сбор товаров...")

	# 1. Сначала получаем курс (1 запрос)
	usd_rate = await get_current_usd_rate()
	products = await parse_products_from_category(target_category)

	product_links = extract_products_links(products)
	logger.info(f"Найдено {len(product_links)} объявлений.")

	# 2. Передаем usd_rate внутрь каждой задачи
	detail_tasks = [parse_product_details(link, usd_rate, target_category)
					for link in product_links]

	all_details = await asyncio.gather(*detail_tasks)

	for data in all_details:
		if data and filters.match(data):
			logger.info("Найден товар: %s", data.get("title"))

# Запуск программы
if __name__ == "__main__":
	try:
		asyncio.run(run_parsing())
	except KeyboardInterrupt:
		pass
	finally:
		# Закрытие клиента отключено:
		# при завершении возникает RuntimeError "Event loop is closed".
		logger.info("Парсинг завершен")
