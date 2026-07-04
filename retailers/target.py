"""
Target stock checker.

Target's product pages are rendered client-side, so we hit the same
"redsky" data API the website itself calls to fetch price/availability
JSON. This endpoint is public (no login/key needed) but undocumented,
so Target can change its shape at any time — if this starts returning
unexpected data, that's the most likely reason.
"""
import logging
from .common import get_session, StockResult

log = logging.getLogger(__name__)

# Generic "web" API key Target's own site uses for anonymous product lookups.
# This is not a secret tied to any account.
REDSKY_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e6"
REDSKY_URL = "https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"


def check(tcin: str, product_label: str) -> StockResult:
    url = f"https://www.target.com/p/-/A-{tcin}"
    session = get_session()
    params = {
        "key": REDSKY_KEY,
        "tcin": tcin,
        "pricing_store_id": "3991",  # generic store id; shipping availability doesn't need a real local store
    }
    try:
        resp = session.get(REDSKY_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        item = data["data"]["product"]["item"]
        name = item.get("product_description", {}).get("title", product_label)
        fulfillment = data["data"]["product"].get("fulfillment", {})
        shipping = fulfillment.get("shipping_options", {})
        purchasable = shipping.get("availability_status") == "IN_STOCK"
    except Exception as exc:
        log.warning("Target check failed for tcin %s: %s", tcin, exc)
        return StockResult("target", product_label, url, False, note=f"error: {exc}")

    return StockResult(
        retailer="target",
        product_label=name,
        url=url,
        in_stock=purchasable,
        note=f"shipping_status={shipping.get('availability_status')}",
    )
