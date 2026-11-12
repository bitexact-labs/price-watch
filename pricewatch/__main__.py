"""pricewatch START_URL [--db prices.db] [--xlsx prices.xlsx] [--max-pages N] [--delay 0.5] [--telegram]"""
import argparse, sys, time
from datetime import datetime

from .fetch import Fetcher
from .notify import format_changes, send
from .parse import catalog_page
from .store import Store
from . import xlsx


def crawl(start, fetcher, max_pages=1000, log=print):
    url, items, pages = start, [], 0
    while url and pages < max_pages:
        found, url = catalog_page(fetcher.get(url), url)
        items += found; pages += 1
        log(f"page {pages}: {len(found)} items")
    return items, pages


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pricewatch", description="Scrape a catalog, track price and stock changes, export to Excel, alert in Telegram.")
    ap.add_argument("start", help="first catalog page, e.g. https://books.toscrape.com/catalogue/page-1.html")
    ap.add_argument("--db", default="prices.db")
    ap.add_argument("--xlsx", help="write the current catalog to this .xlsx file")
    ap.add_argument("--max-pages", type=int, default=1000)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests to the same site (be polite)")
    ap.add_argument("--telegram", action="store_true", help="send changes to TELEGRAM_TOKEN / TELEGRAM_CHAT_ID")
    a = ap.parse_args(argv)
    t0 = time.time()
    f = Fetcher(delay=a.delay)
    items, pages = crawl(a.start, f, a.max_pages, log=lambda s: print(s, file=sys.stderr))
    st = Store(a.db)
    first_run = not st.rows()
    changes = st.update(items)
    print(f"{len(items)} items from {pages} pages in {time.time() - t0:.1f} s, {f.requests} requests; "
          + ("first run, baseline saved" if first_run else f"{len(changes)} changes"))
    if not first_run and changes:
        print(format_changes(changes))
        if a.telegram:
            print("telegram:", "sent" if send(format_changes(changes)) else "not sent (set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)")
    if a.xlsx:
        rows = [[r["title"], r["price"], r["currency"], "yes" if r["in_stock"] else "no", r["rating"], r["url"],
                 datetime.fromtimestamp(r["first_seen"]), datetime.fromtimestamp(r["last_seen"])] for r in st.rows()]
        xlsx.write(a.xlsx, ["Title", "Price", "Currency", "In stock", "Rating", "URL", "First seen", "Last seen"], rows, "Catalog")
        print("excel:", a.xlsx)


if __name__ == "__main__":
    main()
