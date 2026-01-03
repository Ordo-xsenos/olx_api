import requests, bs4
import json
import re
from urllib.parse import urljoin
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

main_url = "https://www.olx.uz"

# Настройка сессии с retry и тайм-аутом
SESSION = requests.Session()
RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)
SESSION.mount("https://", ADAPTER)
SESSION.mount("http://", ADAPTER)
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; olx-scraper/1.0)"})
DEFAULT_TIMEOUT = 10  # seconds
REQUEST_DELAY = 0.2   # seconds между запросами (rate limit)


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return resp.text
    except Exception as e:
        logger.error("Ошибка запроса %s: %s", url, e)
        return None


def get_text_or_default(parent, tag, cls, default="None"):
    if parent is None:
        return default
    el = parent.find(tag, class_=cls)
    return el.get_text(strip=True) if el else default


def parse_category_urls(url):
    category_urls = []

    text = fetch(url)
    if not text:
        return category_urls

    soup = bs4.BeautifulSoup(text, 'html.parser')
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
            category_urls.append(href if href.startswith('http') else urljoin(url, href))
    return category_urls


def parse_products_from_category(category_url):
    text = fetch(category_url)
    if not text:
        return []
    category_soup = bs4.BeautifulSoup(text, 'html.parser')
    container = category_soup.find("div", class_="css-j0t2x2")
    if not container:
        return []
    items = container.find_all("div", class_="css-1sw7q4x")
    return items or []


def parse_product_details(product):
    # Используем helper get_text_or_default для безопасности
    title = get_text_or_default(product, "h4", "css-hzlye5")
    price = get_text_or_default(product, "p", "css-blr5zl")
    location_and_date = get_text_or_default(product, "p", "css-1b24pxk")
    status = get_text_or_default(product, "span", "css-1mqzepw")

    return {
        "title": title,
        "price": price,
        "status": status,
        "location-and-date": location_and_date,
    }


def extract_products_links(products):
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


def parse_real_estate_details(ad_url):
    text = fetch(ad_url)
    if not text:
        return {}
    soup = bs4.BeautifulSoup(text, "html.parser")

    details = {}

    details["title"] = get_text_or_default(soup, "h4", "css-1au435n")
    details["date"] = get_text_or_default(soup, "span", "css-7b83xv")
    details["price"] = get_text_or_default(soup, "h3", "css-yauxmy")
    location_div = soup.find("div", class_="css-1deibjd")
    details["precise_location"] = get_text_or_default(location_div, "p", "css-9pna1a")
    details["location"] = get_text_or_default(location_div, "p", "css-3cz5o2")
    parameters_div = soup.find("div", class_="css-6zsv65")
    parameters_list = []
    if parameters_div:
        parameters_containers = parameters_div.find_all("p", class_="css-13x8d99")
        for parameter in parameters_containers:
            parameter = parameter.get_text()
            parameters_list.append(parameter)
    details["parameters"] = parameters_list
    details["ID"] = get_text_or_default(soup, "span", "css-ooacec")

    for row in soup.select("div[data-testid='ad-parameters'] div"):
        spans = row.select("span")
        if len(spans) < 2:
            continue
        key = spans[0].get_text(strip=True)
        value = spans[1].get_text(strip=True)
        details[key] = value

    description = soup.select_one("div[data-testid='ad-description']")
    if description:
        details["Описание"] = description.get_text(strip=True)

    return details


class RealEstate:
    def __init__(self, base, building_details):
        self.base = base
        self.building_details = building_details

    def format(self):
        lines = [f"🏠 {self.base['title']}",
                 "",
                 f"Область: {self.building_details.get('Область')}",
                 f"Город: {self.building_details.get('Город')}",
                 f"Район: {self.building_details.get('Район')}",
                 "",
                 f"ID: {self.building_details.get('ID')}",
                 ""]

        for k, v in self.building_details.items():
            if k in ("Область", "Город", "Район", "ID"):
                continue
            lines.append(f"{k}: {v}")

        lines.append("")
        lines.append(f"Цена: {self.base['price']}")

        return "\n".join(lines)

def parse_price_value(text: str):
    """Парсит строку цены и возвращает (value: float|None, currency: str).
    Поддерживает UZS, USD, EUR и пометки вроде 'договор'/'торг'.
    """
    if not text:
        return None, "UNKNOWN"

    s = text.lower().replace('\u00A0', ' ').strip()

    # если указано, что цена по договорённости
    if 'договор' in s or 'торг' in s or 'по договорённости' in s:
        return None, 'NEGOTIABLE'

    # Ищем число (с возможными разделителями тысяч/десятичных)
    m = re.search(r"(\d{1,3}(?:[\s\u00A0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)", s)
    if not m:
        return None, 'UNKNOWN'

    num = m.group(1)
    # удаляем пробелы в тысячах
    num = num.replace('\u00A0', '').replace(' ', '').replace(',', '.')
    try:
        value = float(num)
    except ValueError:
        return None, 'UNKNOWN'

    # Определяем валюту
    if '$' in s or 'usd' in s or 'y.e' in s:
        currency = 'USD'
    else:
        # если явно не указано — считаем UZS
        currency = 'UZS'

    return value, currency


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
            value, currency = parse_price_value(item["price"])
            if value is None:
                return False

            if currency == "EUR":
                value *= 14000   # примерный курс
            elif currency == "USD":
                value *= 12500

            return value <= max_price_uzs

        self.rules.append(_f)
        return self

    def city(self, city):
        self.rules.append(lambda item: city in item["location-and-date"])
        return self

    def status(self, status):
        self.rules.append(lambda item: item["status"] == status)
        return self

    def keyword(self, word):
        self.rules.append(lambda item: word.lower() in item["title"].lower())
        return self

    def date(self, text):
        self.rules.append(lambda item: text in item["location-and-date"])
        return self

    def match(self, item):
        return all(rule(item) for rule in self.rules)

filters = (Filters()
           .price_below(700_000)
           .city("Ташкент")
           .status("Новый")
           .date("Сегодня"))

results = []

for category_url in parse_category_urls(main_url):
    try:
        products = parse_products_from_category(category_url)

        # специальная логика для недвижимости
        if category_url == urljoin(main_url, "nedvizhimost/") or category_url.rstrip('/') == "https://www.olx.uz/nedvizhimost":
            try:
                products = parse_products_from_category(urljoin(category_url, "kvartiry/"))
                product_links = extract_products_links(products)
                for link in product_links:
                    try:
                        building_details = parse_real_estate_details(link)
                        print(building_details)
                    except Exception as e:
                        logger.exception("Ошибка парсинга детали недвижимости %s: %s", link, e)
            except Exception as e:
                logger.exception("Ошибка получения раздела недвижимости: %s", e)

        for product in products:
            try:
                details = parse_product_details(product)

                if filters.match(details):
                    pass
                    #print(details)
            except Exception as e:
                logger.exception("Ошибка парсинга объявления в %s: %s", category_url, e)
    except Exception as e:
        logger.exception("Ошибка обработки категории %s: %s", category_url, e)



