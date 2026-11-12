"""SQLite: one row per item, a price history, and the list of changes since the previous run."""
import sqlite3, time

SCHEMA = """
create table if not exists items(url text primary key, title text, price real, currency text, in_stock int, rating int,
                                 first_seen real, last_seen real);
create table if not exists history(url text, ts real, price real, in_stock int);
create index if not exists history_url on history(url, ts);
"""


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def update(self, items, now=None):
        """Saves a full scrape; returns a list of changes: new item, price up/down, back in stock, out of stock, gone."""
        now = now or time.time()
        old = {r["url"]: r for r in self.db.execute("select * from items")}
        changes, seen = [], set()
        with self.db:
            for it in items:
                u = it["url"]; seen.add(u)
                o = old.get(u)
                if o is None:
                    changes.append({"kind": "new", **it})
                else:
                    if o["price"] is not None and it["price"] is not None and abs(o["price"] - it["price"]) >= 0.005:
                        changes.append({"kind": "price_down" if it["price"] < o["price"] else "price_up", "old_price": o["price"], **it})
                    if bool(o["in_stock"]) != it["in_stock"]:
                        changes.append({"kind": "back_in_stock" if it["in_stock"] else "out_of_stock", **it})
                if o is None or o["price"] != it["price"] or bool(o["in_stock"]) != it["in_stock"]:
                    self.db.execute("insert into history values(?,?,?,?)", (u, now, it["price"], int(it["in_stock"])))
                self.db.execute("insert into items values(?,?,?,?,?,?,?,?) on conflict(url) do update set title=excluded.title, "
                                "price=excluded.price, currency=excluded.currency, in_stock=excluded.in_stock, rating=excluded.rating, "
                                "last_seen=excluded.last_seen",
                                (u, it["title"], it["price"], it["currency"], int(it["in_stock"]), it["rating"], now, now))
        changes += [{"kind": "gone", **dict(o)} for u, o in old.items() if u not in seen and o["last_seen"] >= max(r["last_seen"] for r in old.values())]
        return changes

    def rows(self):
        return [dict(r) for r in self.db.execute("select title, price, currency, in_stock, rating, url, first_seen, last_seen from items order by title")]

    def history(self, url):
        return [dict(r) for r in self.db.execute("select ts, price, in_stock from history where url=? order by ts", (url,))]
