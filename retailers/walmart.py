"""
Walmart stock checker.

Walmart has no easy public product API and runs aggressive bot detection
(PerimeterX), so this checker falls back to plain HTML scraping and looks
for common "out of stock" phrases. This is the least reliable checker of
the four:
  - Walmart may serve a CAPTCHA/challenge page instead of the product page
    to a plain `requests` client, which will show up as an "unknown" result.
  - If that happens often, see the README section on using Selenium/
    Playwright with a real headless browser instead, and slow down your
    polling interval so you don't get soft-blocked.
"""
import logging
import re
from .common import get_session, StockResult

log = logging.getLogger(__name__)

OUT_OF_STOCK_PHRASES = [
    "out of stock",
    "currently unavailable",
    "sold out",
]


def check(url: str, product_label: str) -> StockResult:
    session = get_session()
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text.lower()
    except Exception as exc:
        log.warning("Walmart check failed for %s: %s", url, exc)
        return StockResult("walmart", product_label, url, False, note=f"error: {exc}")

    if "robot or human" in html or "px-captcha" in html:
        return StockResult(
            "walmart", product_label, url, False,
            note="Blocked by bot-detection challenge page — result unknown, not confirmed out of stock",
        )

    is_out = any(phrase in html for phrase in OUT_OF_STOCK_PHRASES)
    has_add_to_cart = "add to cart" in html

    # Only call it in-stock if we see "add to cart" AND no out-of-stock phrase.
    in_stock = has_add_to_cart and not is_out

    title_match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    name = title_match.group(1).strip() if title_match else product_label

    return StockResult(
        retailer="walmart",
        product_label=name,
        url=url,
        in_stock=in_stock,
        note=f"add_to_cart_seen={has_add_to_cart} oos_phrase_seen={is_out}",
    )
