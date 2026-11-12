"""HTML -> items, with the standard library parser (no BeautifulSoup needed for a well-formed catalog)."""
from html.parser import HTMLParser
from urllib.parse import urljoin
import re

RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class _Catalog(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.items, self.next, self._it, self._field = base, [], None, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "").split()
        if tag == "article" and "product_pod" in cls:
            self._it = {"title": "", "url": "", "price": None, "currency": "", "in_stock": False, "rating": None}
        elif self._it is not None:
            if tag == "a" and "title" in a:
                self._it["title"], self._it["url"] = a["title"], urljoin(self.base, a["href"])
            elif tag == "p" and "star-rating" in cls:
                self._it["rating"] = next((RATING[c] for c in cls if c in RATING), None)
            elif tag == "p" and "price_color" in cls:
                self._field = "price"
            elif tag == "p" and "availability" in cls:
                self._field = "stock"
        if tag == "li" and "next" in cls:
            self._field = "next"
        elif tag == "a" and self._field == "next":
            self.next, self._field = urljoin(self.base, a["href"]), None

    def handle_data(self, data):
        if self._field == "price" and data.strip():
            m = re.match(r"\s*([^\d\s.,]*)\s*([\d.,]+)", data)
            if m:
                self._it["currency"], self._it["price"] = m[1], float(m[2].replace(",", ""))
            self._field = None
        elif self._field == "stock" and data.strip():
            self._it["in_stock"] = "in stock" in data.lower()
            self._field = None

    def handle_endtag(self, tag):
        if tag == "article" and self._it is not None:
            if self._it["url"]:
                self.items.append(self._it)
            self._it = None


def catalog_page(html, base):
    """Returns (items, next_page_url or None)."""
    p = _Catalog(base)
    p.feed(html)
    return p.items, p.next
