#!/usr/bin/env python3
"""
Pokemon Ascended Heroes stock monitor.

Checks Costco, Best Buy, Target, and Walmart for the product(s) configured
in config.yaml, and sends an email / free carrier-SMS alert the moment one
comes back in stock. Does NOT purchase anything automatically.

Usage:
    python3 monitor.py            # run one check pass and exit
    python3 monitor.py --loop     # run forever, sleeping check_interval_minutes between passes

Designed to also be run as a one-shot job from cron or a systemd timer
(see README.md) rather than looping forever, which is usually the more
robust option on a server.
"""
import argparse
import json
import logging
import os
import random
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from retailers import bestbuy, target, walmart, costco
from retailers.common import StockResult
from notify import send_alert

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("monitor")


def load_config() -> dict:
    with open(BASE_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def run_checks(cfg: dict) -> list[StockResult]:
    results: list[StockResult] = []
    retailers_cfg = cfg.get("retailers", {})
    product_label = cfg.get("product_name", "Pokemon TCG product")

    bb_cfg = retailers_cfg.get("bestbuy", {})
    if bb_cfg.get("enabled"):
        api_key = os.environ.get("BESTBUY_API_KEY", "")
        for sku in bb_cfg.get("skus", []):
            results.append(bestbuy.check(sku, api_key, product_label))

    tgt_cfg = retailers_cfg.get("target", {})
    if tgt_cfg.get("enabled"):
        for tcin in tgt_cfg.get("tcins", []):
            results.append(target.check(tcin, product_label))

    wm_cfg = retailers_cfg.get("walmart", {})
    if wm_cfg.get("enabled"):
        for url in wm_cfg.get("urls", []):
            results.append(walmart.check(url, product_label))

    cco_cfg = retailers_cfg.get("costco", {})
    if cco_cfg.get("enabled"):
        for url in cco_cfg.get("urls", []):
            results.append(costco.check(url, product_label))

    return results


def result_key(r: StockResult) -> str:
    return f"{r.retailer}:{r.url}"


def process_results(results: list[StockResult], state: dict) -> None:
    for r in results:
        key = result_key(r)
        was_in_stock = state.get(key, {}).get("in_stock", False)

        status = "IN STOCK" if r.in_stock else "out of stock"
        log.info("[%s] %s -> %s (%s)", r.retailer.upper(), r.product_label, status, r.note)

        # Only alert on the *transition* from out-of-stock to in-stock,
        # so you don't get spammed every single check while it stays in stock.
        if r.in_stock and not was_in_stock:
            subject = f"🚨 IN STOCK: {r.product_label} @ {r.retailer.title()}"
            body = f"{r.product_label} is now available at {r.retailer.title()}!\n\n{r.url}"
            send_alert(subject, body)

        state[key] = {"in_stock": r.in_stock, "product_label": r.product_label}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Run forever instead of a single pass")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    cfg = load_config()
    state = load_state()

    def one_pass():
        results = run_checks(cfg)
        process_results(results, state)
        save_state(state)

    if not args.loop:
        one_pass()
        return

    interval = cfg.get("check_interval_minutes", 10) * 60
    jitter = cfg.get("jitter_seconds", 30)
    log.info("Starting loop mode: checking every ~%d minutes", interval // 60)
    while True:
        one_pass()
        sleep_time = interval + random.randint(-jitter, jitter)
        time.sleep(max(30, sleep_time))


if __name__ == "__main__":
    main()
