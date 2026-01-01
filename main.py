import requests, bs4
import json
import re

main_url = "https://www.olx.uz"

def get_text_or_default(parent, tag, cls, default="None"):
    el = parent.find(tag, class_=cls)
    return el.get_text(strip=True) if el else default

def parse_category_urls(url):
    category_urls = []

    res = requests.get(url)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    category = soup.find_all("div", class_="css-1rwzo2t")
    link_tag = category[0].find_all("a") # очень странно список в 1 элемент
    for link in link_tag:
        href = link.get("href") # href последней категории очень длинный
        if link_tag[-1] != link:  # пропускаем последний элемент потому что там уже абсолютный URL
            category_urls.append(url + href)
        else:
            category_urls.append(href)
    return category_urls

def parse_products_from_category(category_url):
    resp = requests.get(category_url)
    resp.raise_for_status()
    category_soup = bs4.BeautifulSoup(resp.text, 'html.parser')
    items = category_soup.find("div", class_="css-j0t2x2").find_all("div", class_="css-1sw7q4x")
    return items

def parse_product_details(product):
    title = product.find("h4", class_="css-hzlye5")
    title = title.get_text() if title else "None"

    price = product.find("p", class_="css-blr5zl")
    price = price.get_text() if price else "None"

    location_and_date = product.find("p", class_="css-1b24pxk")
    location_and_date = location_and_date.get_text() if location_and_date else "None"

    status = product.find("span", class_="css-1mqzepw")
    status = status.get_text() if status else "None"

    return {
        "title": title,
        "price": price,
        "status": status,
        "location-and-date": location_and_date,
    }

def parse_price_value(text: str):
    text = text.lower().replace(" ", "")

    if "договор" in text:
        return None, "NEGOTIABLE"

    m = re.search(r'(\d+(?:[.,]\d+)?)', text)
    if not m:
        return None, "UNKNOWN"

    value = float(m.group(1).replace(",", "."))

    if "y.e" in text or "eur" in text or "$" in text:
        currency = "USD"
    else:
        currency = "UZS"

    return value, currency

def extract_products_links(products):
    links = []

    for product in products:
        a = product.find("a", href=True)
        if not a:
            continue

        href = a["href"]
        if not href.startswith("http"):
            href = main_url + href

        links.append(href)

    return links

def parse_real_estate_details(ad_url):
    resp = requests.get(ad_url)
    resp.raise_for_status()
    soup = bs4.BeautifulSoup(resp.text, "html.parser")

    details = {}

    details["title"] = get_text_or_default(soup, "h4", "css-1au435n")
    details["date"] = get_text_or_default(soup, "span", "css-7b83xv")
    location_div = soup.find("div", class_="css-1deibjd")
    details["precise_location"] = get_text_or_default(location_div, "p", "css-9pna1a")
    details["location"] = get_text_or_default(location_div, "p", "css-3cz5o2")
    details["ID"] = get_text_or_default(soup, "span", "css-ooacec")

    for row in soup.select("div[data-testid='ad-parameters'] div"):
        key = row.select_one("span").get_text(strip=True)
        value = row.select("span")[1].get_text(strip=True)
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
    products = parse_products_from_category(category_url)

    # специальная логика для недвижимости
    if category_url == "https://www.olx.uz/nedvizhimost/":
        products = parse_products_from_category(category_url + "kvartiry/")
        product_links = extract_products_links(products)
        for link in product_links:
            building_details = parse_real_estate_details(link)
            print(building_details)

    for product in products:
        details = parse_product_details(product)

        if filters.match(details):
            pass
            #print(details)
