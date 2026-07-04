"""
Best Buy stock checker.

Uses Best Buy's official, free Products API instead of scraping the page.
This is far more reliable than HTML scraping and won't get you IP-blocked.
Get a free key here: https://developer.bestbuy.com/
"""
import logging
from .common import get_session, StockResult

log = logging.getLogger(__name__)

API_URL = "https://api.bestbuy.com/v1/products/{sku}.json"


def check(sku: str, api_key: str, product_label: str) -> StockResult:
    url = f"https://www.bestbuy.com/site/{sku}.p"

    if not api_key:
        return StockResult(
            "bestbuy", product_label, url, False,
            note="No BESTBUY_API_KEY set in .env — skipping (get a free key at developer.bestbuy.com)",
        )

    session = get_session()
    params = {
        "apiKey": api_key,
        "format": "json",
        "show": "sku,name,onlineAvailability,inStoreAvailability,url",
    }
    try:
        resp = session.get(API_URL.format(sku=sku), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network hiccup, bad sku, rate limit, etc.
        log.warning("Best Buy check failed for sku %s: %s", sku, exc)
        return StockResult("bestbuy", product_label, url, False, note=f"error: {exc}")

    online = bool(data.get("onlineAvailability"))
    in_store = bool(data.get("inStoreAvailability"))
    name = data.get("name", product_label)

    return StockResult(
        retailer="bestbuy",
        product_label=name,
        url=data.get("url", url),
        in_stock=online or in_store,
        note=f"online={online} in_store={in_store}",
    )
