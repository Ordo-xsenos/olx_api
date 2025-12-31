import requests, bs4
import json
import re

main_url = "https://www.olx.uz"

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
    if title:
        title = title.get_text()
    else:
        title = "Some error in title parsing"
    price = product.find("p", class_="css-blr5zl")
    if price:
        price = price.get_text()
    else:
        price = "Some error in price parsing"
    location_and_date = product.find("p", class_="css-1b24pxk")
    if location_and_date:
        location_and_date = location_and_date.get_text()
    else:
        location_and_date = "Some error in location and date parsing"
    status = product.find("span", class_="css-1mqzepw")
    if status:
        status = status.get_text()
    else:
        status = "Some error in status parsing"
    return {
        "title": title,
        "price": price,
        "status": status,
        "location-and-date": location_and_date
    }

def parse_price_value(text: str):
    text = text.lower().replace(" ", "")

    if "договор" in text:
        return None, "NEGOTIABLE"

    m = re.search(r'(\d+(?:[.,]\d+)?)', text)
    if not m:
        return None, "UNKNOWN"

    value = float(m.group(1).replace(",", "."))

    if "y.e" in text or "€" in text or "eur" in text:
        currency = "EUR"
    elif "usd" in text or "$" in text:
        currency = "USD"
    else:
        currency = "UZS"

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
    products = parse_products_from_category(category_url)
    for product in products:
        details = parse_product_details(product)

        if filters.match(details):
            print(details)

