import io, sys, urllib.error, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pricewatch.fetch import Fetcher
from pricewatch.notify import format_changes, send
from pricewatch.parse import catalog_page
from pricewatch.store import Store
from pricewatch import xlsx
from pricewatch.__main__ import crawl

FX = ROOT / "tests" / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"


def test_parse_list_page():
    items, nxt = catalog_page((FX / "list-1.html").read_text(), BASE + "page-1.html")
    assert len(items) == 20 and nxt == BASE + "page-2.html"
    a = items[0]
    assert a == {"title": "A Light in the Attic", "url": BASE + "a-light-in-the-attic_1000/index.html",
                 "price": 51.77, "currency": "£", "in_stock": True, "rating": 3}
    assert all(i["price"] > 0 and 1 <= i["rating"] <= 5 for i in items)


def test_last_page_has_no_next():
    items, nxt = catalog_page((FX / "list-50.html").read_text(), BASE + "page-50.html")
    assert len(items) == 20 and nxt is None


class FakeWeb:
    """Serves fixtures instead of the network; counts calls; can fail the first N requests."""
    def __init__(self, pages, fail_first=0, robots=b"User-agent: *\nAllow: /\n"):
        self.pages, self.fail, self.robots, self.calls = pages, fail_first, robots, []

    def __call__(self, req, timeout):
        url = req.full_url; self.calls.append(url)
        if url.endswith("/robots.txt"):
            if self.robots is None:
                raise urllib.error.HTTPError(url, 404, "nf", {}, None)
            return io.BytesIO(self.robots)
        if self.fail:
            self.fail -= 1
            raise urllib.error.HTTPError(url, 503, "busy", {}, None)
        return io.BytesIO(self.pages[url].encode())


def two_pages():
    p1 = (FX / "list-1.html").read_text()
    return {BASE + "page-1.html": p1, BASE + "page-2.html": (FX / "list-50.html").read_text()}


def test_crawl_follows_next_and_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    web = FakeWeb(two_pages(), fail_first=1)
    items, pages = crawl(BASE + "page-1.html", Fetcher(delay=0, opener=web), log=lambda s: None)
    assert pages == 2 and len(items) == 40
    assert web.calls.count(BASE + "page-1.html") == 2   # one 503, one retry


def test_robots_disallow_is_respected():
    web = FakeWeb(two_pages(), robots=b"User-agent: *\nDisallow: /catalogue/\n")
    try:
        Fetcher(delay=0, opener=web).get(BASE + "page-1.html")
        assert False, "should refuse"
    except PermissionError:
        pass
    assert web.calls == ["https://books.toscrape.com/robots.txt"]


def test_missing_robots_means_allowed():
    web = FakeWeb(two_pages(), robots=None)
    assert "A Light in the Attic" in Fetcher(delay=0, opener=web).get(BASE + "page-1.html")


def test_change_detection(tmp_path):
    items, _ = catalog_page((FX / "list-1.html").read_text(), BASE + "page-1.html")
    st = Store(tmp_path / "p.db")
    assert len(st.update(items, now=1)) == 20                      # first run: all new
    assert st.update(items, now=2) == []                           # nothing changed
    changed = [dict(i) for i in items]
    changed[0]["price"] = 40.00                                    # cheaper
    changed[1]["price"] += 5                                       # more expensive
    changed[2]["in_stock"] = False                                 # sold out
    del changed[3]                                                 # removed from the site
    kinds = sorted(c["kind"] for c in st.update(changed, now=3))
    assert kinds == ["gone", "out_of_stock", "price_down", "price_up"]
    assert [h["price"] for h in st.history(items[0]["url"])] == [51.77, 40.0]
    msg = format_changes(st.update(changed, now=4) or [{"kind": "price_down", "title": "A Light in the Attic", "price": 40.0, "old_price": 51.77, "currency": "£"}])
    assert "price down: 1" in msg and "was £51.77" in msg


def test_xlsx_is_valid_zip_with_numbers(tmp_path):
    p = tmp_path / "x.xlsx"
    xlsx.write(p, ["Title", "Price"], [["a & <b>", 1.5], ["c", 2]])
    z = zipfile.ZipFile(p)
    sheet = z.read("xl/worksheets/sheet1.xml").decode()
    assert "a &amp; &lt;b&gt;" in sheet and "<v>1.5</v>" in sheet and 'autoFilter ref="A1:B3"' in sheet
    assert {"[Content_Types].xml", "xl/workbook.xml", "xl/styles.xml"} <= set(z.namelist())


def test_telegram_needs_token():
    assert send("hi", token="", chat="") is False
    sent = []
    class R(io.BytesIO): pass
    def opener(req, timeout):
        sent.append(req.full_url); return R(b'{"ok": true}')
    assert send("hi", token="T", chat="1", opener=opener) is True and sent == ["https://api.telegram.org/botT/sendMessage"]
