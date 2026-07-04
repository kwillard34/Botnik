"""
Costco stock checker.

Costco has no public product API, and availability is often tied to your
local warehouse or delivery zip code. This is a best-effort text scrape
of the product page and is the least reliable of the four checkers.
"""
import logging
import re
from .common import get_session, StockResult

log = logging.getLogger(__name__)

OUT_OF_STOCK_PHRASES = [
    "out of stock",
    "currently unavailable",
    "sold out",
    "temporarily out of stock",
]

ADD_TO_CART_PHRASES = [
    "add to cart",
]


def check(url: str, product_label: str) -> StockResult:
    session = get_session()
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text.lower()
    except Exception as exc:
        log.warning("Costco check failed for %s: %s", url, exc)
        return StockResult("costco", product_label, url, False, note=f"error: {exc}")

    is_out = any(phrase in html for phrase in OUT_OF_STOCK_PHRASES)
    has_add_to_cart = any(phrase in html for phrase in ADD_TO_CART_PHRASES)
    in_stock = has_add_to_cart and not is_out

    title_match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    name = title_match.group(1).strip() if title_match else product_label

    return StockResult(
        retailer="costco",
        product_label=name,
        url=url,
        in_stock=in_stock,
        note=f"add_to_cart_seen={has_add_to_cart} oos_phrase_seen={is_out}",
    )
