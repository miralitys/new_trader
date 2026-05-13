#!/usr/bin/env python3
"""Build a Binance USD-M futures archive inventory.

This is a lightweight first pass before expensive strategy backtests. It uses
the public Binance data archive, not the blocked trading API, and records which
symbols have fresh 1m archives plus the available monthly history range.
"""

import argparse
import csv
import datetime as dt
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S3_BUCKET_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
ARCHIVE_BASE_URL = "https://data.binance.vision/data/futures/um/daily/klines"


def s3_url(prefix, delimiter=None):
    params = {"prefix": prefix}
    if delimiter:
        params["delimiter"] = delimiter
    return f"{S3_BUCKET_URL}?{urllib.parse.urlencode(params)}"


def fetch_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def list_common_prefix_symbols(prefix):
    text = fetch_text(s3_url(prefix, delimiter="/"))
    return sorted(set(re.findall(r"<Prefix>" + re.escape(prefix) + r"([^/]+)/</Prefix>", text)))


def list_months(symbol):
    prefix = f"data/futures/um/monthly/klines/{symbol}/1m/"
    text = fetch_text(s3_url(prefix))
    root = ET.fromstring(text)
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    months = []
    pattern = re.compile(rf"{re.escape(symbol)}-1m-(\d{{4}}-\d{{2}})\.zip$")
    for item in root.findall("s3:Contents", namespace):
        key = item.findtext("s3:Key", default="", namespaces=namespace)
        match = pattern.search(key)
        if match:
            months.append(match.group(1))
    return sorted(set(months))


def archive_zip_url(symbol, day):
    safe_symbol = urllib.parse.quote(symbol, safe="")
    day_text = day.isoformat()
    return f"{ARCHIVE_BASE_URL}/{safe_symbol}/1m/{safe_symbol}-1m-{day_text}.zip"


def head_ok(url):
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status == 200
    except Exception:
        return False


def active_on_day(symbol, day):
    return head_ok(archive_zip_url(symbol, day))


def latest_active_day(symbols, lookback_days):
    today = dt.datetime.utcnow().date()
    days = [today - dt.timedelta(days=i) for i in range(1, lookback_days + 1)]
    for day in days:
        with ThreadPoolExecutor(max_workers=64) as executor:
            active = list(executor.map(lambda symbol: active_on_day(symbol, day), symbols))
        active_symbols = [symbol for symbol, ok in zip(symbols, active) if ok]
        if active_symbols:
            return day, active_symbols
    return None, []


def quote_asset(symbol):
    for quote in ("USDT", "USDC", "BUSD"):
        if symbol.endswith(quote):
            return quote
    return "OTHER"


def base_asset(symbol):
    quote = quote_asset(symbol)
    if quote == "OTHER":
        return symbol
    return symbol[: -len(quote)]


def is_delivery(symbol):
    return "_" in symbol


def is_ascii(symbol):
    try:
        symbol.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_report(path, rows, active_day):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    active_usdt = [row for row in rows if row["is_active"] and row["quote_asset"] == "USDT" and not row["is_delivery"]]
    active_usdc = [row for row in rows if row["is_active"] and row["quote_asset"] == "USDC" and not row["is_delivery"]]
    active_ascii_usdt = [row for row in active_usdt if row["is_ascii"]]
    active_non_ascii_usdt = [row for row in active_usdt if not row["is_ascii"]]
    historical_usdt = [row for row in rows if row["quote_asset"] == "USDT" and not row["is_delivery"]]

    history_buckets = {
        "24m+": sum(1 for row in active_usdt if int(row["months_count"]) >= 24),
        "12-23m": sum(1 for row in active_usdt if 12 <= int(row["months_count"]) < 24),
        "<12m": sum(1 for row in active_usdt if int(row["months_count"]) < 12),
    }

    top_history = sorted(active_usdt, key=lambda row: (-int(row["months_count"]), row["symbol"]))[:30]

    lines = [
        "# Binance Futures Universe Inventory",
        "",
        "Источник: публичный Binance Futures archive `data/futures/um/*/klines`.",
        "",
        f"Свежий архивный день: `{active_day}`.",
        "",
        "## Counts",
        "",
        "| Срез | Количество |",
        "|---|---:|",
        f"| Все символы с историей в USD-M archive | {len(rows)} |",
        f"| Исторические USDT без квартальных `_` | {len(historical_usdt)} |",
        f"| Активные USDT без квартальных `_` | {len(active_usdt)} |",
        f"| Активные USDT ASCII | {len(active_ascii_usdt)} |",
        f"| Активные USDT non-ASCII | {len(active_non_ascii_usdt)} |",
        f"| Активные USDC | {len(active_usdc)} |",
        "",
        "## Active USDT History Depth",
        "",
        "| Глубина истории | Монет |",
        "|---|---:|",
    ]
    for key, value in history_buckets.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Longest Active USDT Histories",
            "",
            "| Symbol | First month | Last month | Months | ASCII |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in top_history:
        lines.append(
            f"| `{row['symbol']}` | {row['first_month']} | {row['last_month']} | "
            f"{row['months_count']} | {row['is_ascii']} |"
        )

    if active_non_ascii_usdt:
        lines.extend(
            [
                "",
                "## Non-ASCII Active USDT",
                "",
                "| Symbol | Months |",
                "|---|---:|",
            ]
        )
        for row in active_non_ascii_usdt:
            lines.append(f"| `{row['symbol']}` | {row['months_count']} |")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Build Binance futures archive inventory.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--save-csv", default="data/binance_futures_universe_inventory.csv")
    parser.add_argument("--save-report", default="strategies/binance-futures-universe-inventory.md")
    args = parser.parse_args()

    daily_symbols = list_common_prefix_symbols("data/futures/um/daily/klines/")
    monthly_symbols = list_common_prefix_symbols("data/futures/um/monthly/klines/")
    all_symbols = sorted(set(daily_symbols) | set(monthly_symbols))

    active_day, active_symbols = latest_active_day(all_symbols, args.lookback_days)
    active_set = set(active_symbols)

    rows = []
    for index, symbol in enumerate(all_symbols, start=1):
        print(f"[{index}/{len(all_symbols)}] {symbol}", flush=True)
        try:
            months = list_months(symbol)
            error = ""
        except Exception as exc:
            months = []
            error = repr(exc)
        rows.append(
            {
                "symbol": symbol,
                "base_asset": base_asset(symbol),
                "quote_asset": quote_asset(symbol),
                "is_active": symbol in active_set,
                "active_day": active_day.isoformat() if active_day else "",
                "is_delivery": is_delivery(symbol),
                "is_ascii": is_ascii(symbol),
                "first_month": months[0] if months else "",
                "last_month": months[-1] if months else "",
                "months_count": len(months),
                "has_12m": len(months) >= 12,
                "has_24m": len(months) >= 24,
                "has_36m": len(months) >= 36,
                "error": error,
            }
        )

    fields = [
        "symbol",
        "base_asset",
        "quote_asset",
        "is_active",
        "active_day",
        "is_delivery",
        "is_ascii",
        "first_month",
        "last_month",
        "months_count",
        "has_12m",
        "has_24m",
        "has_36m",
        "error",
    ]
    save_csv(args.save_csv, rows, fields)
    save_report(args.save_report, rows, active_day)

    active_usdt = [
        row for row in rows if row["is_active"] and row["quote_asset"] == "USDT" and not row["is_delivery"]
    ]
    print(f"symbols with archive history: {len(rows)}")
    print(f"active day: {active_day}")
    print(f"active USDT symbols: {len(active_usdt)}")
    print(f"saved csv: {os.path.abspath(args.save_csv)}")
    print(f"saved report: {os.path.abspath(args.save_report)}")


if __name__ == "__main__":
    main()
