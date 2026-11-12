"""Telegram alerts through the Bot API. Token and chat id come from the environment, never from code."""
import json, os, urllib.request

ICON = {"new": "🆕", "price_down": "🔻", "price_up": "🔺", "back_in_stock": "✅", "out_of_stock": "⛔", "gone": "🗑"}
LABEL = {"new": "new", "price_down": "price down", "price_up": "price up", "back_in_stock": "back in stock", "out_of_stock": "out of stock", "gone": "removed"}


def format_changes(changes, limit=30):
    """Groups changes into one short message (Telegram limit is 4096 chars)."""
    order = ["price_down", "back_in_stock", "price_up", "out_of_stock", "new", "gone"]
    lines = []
    for k in order:
        part = [c for c in changes if c["kind"] == k]
        if not part:
            continue
        lines.append(f"{ICON[k]} {LABEL[k]}: {len(part)}")
        for c in part[:limit]:
            price = f"{c.get('currency', '')}{c['price']:.2f}" if c.get("price") is not None else ""
            was = f" (was {c.get('currency', '')}{c['old_price']:.2f})" if "old_price" in c else ""
            lines.append(f"  • {c['title'][:60]} {price}{was}")
        if len(part) > limit:
            lines.append(f"  … and {len(part) - limit} more")
    text = "\n".join(lines)
    return text[:4000] + ("\n…" if len(text) > 4000 else "")


def send(text, token=None, chat=None, opener=urllib.request.urlopen):
    token, chat = token or os.environ.get("TELEGRAM_TOKEN"), chat or os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat and text):
        return False
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    with opener(req, timeout=20) as r:
        return json.loads(r.read()).get("ok", False)
