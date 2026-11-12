# price-watch

Watch a product catalog and get told when something changes: a price goes down or up, an item sells out or comes back, new items appear or old ones disappear. Every run is saved to SQLite with full price history, and the catalog can be exported to Excel in one flag.

Pure Python 3.10+, **no dependencies** (the `.xlsx` writer and the HTML parser are on the standard library), so it runs on any server or a cheap VPS from cron.

```bash
pip install git+https://github.com/bitexact-labs/price-watch
pricewatch https://books.toscrape.com/catalogue/page-1.html --xlsx catalog.xlsx --telegram
```

The demo target is [books.toscrape.com](https://books.toscrape.com), a sandbox site made for scraping practice. For a real shop only the parser (`pricewatch/parse.py`, ~60 lines) changes; storage, change detection, alerts, export and politeness stay the same.

## A real run

First run saves the baseline:
```
1000 items from 50 pages in 39.2 s, 50 requests; first run, baseline saved
excel: catalog.xlsx
```
Second run, after three products were changed in the saved database to simulate a price move and a restock:
```
1000 items from 50 pages in 38.9 s, 50 requests; 3 changes
🔻 price down: 1
  • A Light in the Attic £51.77 (was £54.77)
✅ back in stock: 1
  • Soumission £50.10
🔺 price up: 1
  • Tipping the Velvet £53.74 (was £51.74)
excel: catalog.xlsx
```
With `--telegram` the same text goes to your chat (set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`). Run it from cron every hour and you have a price monitor.

## What it does carefully

- **Polite by default**: reads `robots.txt` and refuses disallowed pages, waits `--delay` seconds between requests to the same site, sends an honest user agent. It does not bypass captchas, logins or anti-bot protection, and it shouldn't be used to.
- **Doesn't fall over**: retries 429/5xx and network errors with exponential backoff; a 404 is reported, not retried forever.
- **History, not just a snapshot**: a row in `history` is written only when the price or stock actually changes, so the database stays small even after months of hourly runs.
- **Excel without extra libraries**: header row bold and frozen, auto-filter on, numbers stored as numbers (not text). Verified by reading it back with openpyxl without warnings; not yet opened in desktop Excel by us.

## Tests

```bash
python -m pytest tests
```
Run offline against saved pages in `tests/fixtures/`: parsing of list pages (title, URL, price, currency, stock, rating), following pagination to the last page, retry after a 503, `robots.txt` allow/deny/missing, change detection (new, price up/down, out of stock, removed) and price history, `.xlsx` structure and escaping, Telegram call without a real token.

## Need something like this?

Scrapers, price monitors, Telegram bots and data exports, for public data and legal use. More work: [github.com/bitexact-labs](https://github.com/bitexact-labs).

MIT license.
