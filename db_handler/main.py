import bs4
import json
import re
from urllib.parse import urljoin, urlparse
import logging
import httpx
import asyncio
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main_url = "https://www.olx.uz"
# Ограничиваем количество одновременных запросов (чтобы не забанили)
MAX_CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Асинхронный клиент с настройками тайм-аута и заголовков
ASYNC_CLIENT = httpx.AsyncClient(
	timeout=10.0,
	headers={"User-Agent": "Mozilla/5.0 (compatible; olx-scraper/2.0)"},
	follow_redirects=True
)


async def fetch(url: str) -> str | None:
	"""Асинхронное скачивание страницы с ограничением через семафор."""
	async with semaphore:
		try:
			resp = await ASYNC_CLIENT.get(url)
			resp.raise_for_status()
			# Короткая пауза между запросами внутри семафора
			await asyncio.sleep(0.1)
			return resp.text
		except Exception as e:
			logger.error("Ошибка асинхронного запроса %s: %s", url, e)
			return None


def get_text_or_default(parent : BeautifulSoup, tag, cls : str, default="None"):
	"""Безопасно извлекает текст из HTML-элемента.

	Проблема: иногда в parent передаётся строка (или другой объект), и вызов
	parent.find(tag, class_=cls) приводит к тому, что вызывается str.find,
	который не поддерживает keyword-аргумент class_.

	Решение: проверяем, имеет ли parent метод find (и что это не обычная
	строка), и только в этом случае вызываем .find. Если parent — строка или
	NavigableString — возвращаем её обрезанную форму или default.
	"""
	# Если parent пустой (None, пустая строка и т.п.) — возвращаем default
	if not parent:
		return default

	# bs4.element.NavigableString ведёт себя как строка, поэтому отдельно обрабатываем строки
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

	# В общем случае возвращаем default
	return default


async def parse_category_urls(url : str) -> list[str]:
	category_urls = []

	text = await fetch(url)
	if not text:
		return category_urls

	soup = bs4.BeautifulSoup(text, "html.parser")
	category = soup.find_all("div", class_="css-1rwzo2t")
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


async def parse_products_from_category(category_url : str) -> list[bs4.element.Tag]:
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
			current_url = f"{category_url.rstrip('/')}/?page={page_num}"
			page_text = await fetch(current_url)
			if not page_text:
				continue
			soup = bs4.BeautifulSoup(page_text, "html.parser")

		# Находим контейнер и товары
		container = soup.find("div", class_="css-j0t2x2")
		if container:
			items = container.find_all("div", class_="css-1sw7q4x")
			all_items.extend(items)

	return all_items


def extract_products_links(products : list[bs4.element.Tag]) -> list[str]:
	links = []

	for product in products:
		a = product.find("a", href=True)
		if not a:
			continue

		href = a["href"]
		if not href.startswith("http"):
			href = urljoin(main_url, href)

		links.append(href)

	return links


async def parse_product_details(ad_url, usd_rate: int, category: str) -> dict:
	"""Асинхронная версия парсинга деталей объявления."""
	text = await fetch(ad_url)
	if not text:
		return {}
	soup = bs4.BeautifulSoup(text, "html.parser")

	details = {}

	if "nedvizhimost" in ad_url:
		details["category"] = "nedvizhimost"
	else:
		details["category"] = category.removeprefix("https://www.olx.uz/").strip("/")
	details["title"] = get_text_or_default(soup, "h4", "css-1au435n")
	details["date"] = get_text_or_default(soup, "span", "css-7b83xv")
	#--- Логика ЦЕН ---
	raw_price_value = get_text_or_default(soup, "h3", "css-yauxmy")
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
	location_div = soup.find("div", class_="css-1deibjd")
	details["precise_location"] = get_text_or_default(
		location_div, "p", "css-9pna1a"
	)
	details["location"] = get_text_or_default(location_div, "p", "css-3cz5o2")
	parameters_div = soup.find("div", class_="css-6zsv65")
	parameters_list = []
	if parameters_div:
		parameters_containers = parameters_div.find_all(
			"p", class_="css-13x8d99"
		)
		for parameter in parameters_containers:
			parameter = parameter.get_text()
			parameters_list.append(parameter)
	details["parameters"] = parameters_list
	details["olx_id"] = get_text_or_default(soup, "span", "css-ooacec")
	details["url"] = ad_url

	return details


def parse_price_value(text: str) -> tuple[int | None, str]:
	"""Возвращает Decimal для точности."""
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
			return int("12800")  # Fallback курс, если API упал

		data = json.loads(text_response)  # Парсим строку в JSON

		if data.get("result") == "success":
			rate = data["conversion_rates"].get("UZS")
			logger.info(f"Актуальный курс доллара: {rate}")
			return int(rate)
		else:
			logger.error("API вернул ошибку")
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
			value = item["original_price"]
			currency = item["currency"]
			if value is None:
				return False

			if currency == "UZS":
				value /= 12500  # примерный курс

			return value <= max_price_uzs

		self.rules.append(_f)
		return self

	def city(self, city):
		self.rules.append(lambda item: city in item["location"])
		return self

	def keyword(self, word):
		self.rules.append(lambda item: word.lower() in item["title"].lower())
		return self

	def date(self, text):
		self.rules.append(lambda item: text in item["date"])
		return self

	def match(self, item):
		return all(rule(item) for rule in self.rules)


filters = (
	Filters()
	.price_below(1000_000)
	#.city("Ташкент")
	#.date("Сегодня")
)

results = []


async def run_parsing():
	categories = await parse_category_urls(main_url)
	url_dict = {urlparse(url).path: url for url in categories}
	user_input = input("Введите путь категории для парсинга (например, /nedvizhimost/): ").strip()
	if user_input not in url_dict:
		print("Неверный путь категории.")
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
			print(data)

# Запуск программы
if __name__ == "__main__":
	try:
		asyncio.run(run_parsing())
	except KeyboardInterrupt:
		pass
	finally:
		# Закрываем клиент в конце,
		# выходит странная ошибка RuntimeError: Event loop is closed
		# поэтому закомментировал
		#asyncio.run(ASYNC_CLIENT.aclose())
		print("Парсинг завершен")
