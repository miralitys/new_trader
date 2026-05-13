#!/usr/bin/env python3
"""Fast Binance USD-M futures kline archive downloader.

This version is intended for very large intervals like 1m. It preserves the raw
Binance kline columns and avoids per-row datetime conversion.
"""

import argparse
import csv
import io
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHLY_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
DAILY_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
RAW_HEADER = (
    b"open_time_ms,open,high,low,close,volume,close_time_ms,quote_volume,"
    b"trades,taker_buy_base_volume,taker_buy_quote_volume,ignore\n"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Fast download raw Binance Futures klines.")
    parser.add_argument("--symbols-file", default="data/binance_futures_active_usdt_ascii_symbols_2026-05-04.txt")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--interval", default="1m", choices=["1m", "5m", "15m", "1h", "4h"])
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def first_day_of_month(value):
    return date(value.year, value.month, 1)


def next_month(value):
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def month_starts(start_day, end_day):
    current = first_day_of_month(start_day)
    last = first_day_of_month(end_day)
    while current <= last:
        yield current
        current = next_month(current)


def load_symbols(path, limit=None):
    with open(path, encoding="utf-8") as handle:
        symbols = [line.strip().upper() for line in handle if line.strip()]
    symbols = [symbol for symbol in symbols if symbol.endswith("USDT") and "_" not in symbol]
    return symbols[:limit] if limit else symbols


def request_url(url, retries=3):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(url)
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def archive_url(base, symbol, interval, stamp):
    safe_symbol = urllib.parse.quote(symbol, safe="")
    return f"{base}/{safe_symbol}/{interval}/{safe_symbol}-{interval}-{stamp}.zip"


def monthly_url(symbol, interval, month):
    return archive_url(MONTHLY_BASE, symbol, interval, f"{month.year:04d}-{month.month:02d}")


def daily_url(symbol, interval, day):
    return archive_url(DAILY_BASE, symbol, interval, day.isoformat())


def iter_zip_lines(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_names:
            return
        with archive.open(csv_names[0]) as handle:
            for line in handle:
                if not line or not (48 <= line[0] <= 57):
                    continue
                yield line if line.endswith(b"\n") else line + b"\n"


def raw_open_time(line):
    comma = line.find(b",")
    if comma <= 0:
        return None
    try:
        return int(line[:comma])
    except ValueError:
        return None


def fetch_payload(url):
    try:
        return request_url(url), "ok"
    except FileNotFoundError:
        return None, "missing"


def existing_manifest(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["symbol"]: row for row in csv.DictReader(handle)}


def save_manifest(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["symbol", "status", "candles", "start_ms", "end_ms", "files_found", "files_missing", "path", "error"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["symbol"]))


def save_report(path, rows, args, start_day, end_day):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok = [row for row in rows if row["status"] == "ok"]
    partial = [row for row in rows if row["status"] == "partial"]
    empty = [row for row in rows if row["status"] == "empty"]
    errors = [row for row in rows if row["status"] == "error"]
    total = sum(int(row.get("candles") or 0) for row in rows)
    lines = [
        f"# Binance Futures Raw {args.interval} History Download",
        "",
        f"Period: `{start_day}` -> `{end_day}` UTC.",
        f"Symbols total: `{len(rows)}`.",
        f"Full/ok: `{len(ok)}`.",
        f"Partial: `{len(partial)}`.",
        f"Empty/no history: `{len(empty)}`.",
        f"Errors: `{len(errors)}`.",
        f"Total candles saved: `{total}`.",
        "",
        f"Output folder: `{args.out_dir}/`.",
        f"Manifest: `{args.manifest}`.",
        "",
        "Format: raw Binance kline columns with `open_time_ms` and `close_time_ms`.",
    ]
    if errors:
        lines.extend(["", "## Errors", ""])
        for row in errors[:50]:
            lines.append(f"- `{row['symbol']}`: {row['error']}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def download_symbol(symbol, args, start_day, end_day, previous):
    out_path = os.path.join(args.out_dir, f"{symbol}_{args.interval}.csv")
    if (
        not args.overwrite
        and previous
        and previous.get("status") in ("ok", "partial")
        and os.path.exists(out_path)
        and os.path.getsize(out_path) > 0
    ):
        return dict(previous)

    start_ms = int(datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)
    latest_month = first_day_of_month(end_day)
    tmp_path = out_path + ".tmp"
    files_found = 0
    files_missing = 0
    candles = 0
    first_ms = ""
    last_ms = ""

    try:
        os.makedirs(args.out_dir, exist_ok=True)
        with open(tmp_path, "wb") as output:
            output.write(RAW_HEADER)
            for month in month_starts(start_day, end_day):
                month_end = next_month(month) - timedelta(days=1)
                urls = []
                if month < latest_month:
                    urls.append(monthly_url(symbol, args.interval, month))
                else:
                    day = max(month, start_day)
                    final_day = min(month_end, end_day)
                    while day <= final_day:
                        urls.append(daily_url(symbol, args.interval, day))
                        day += timedelta(days=1)

                for url in urls:
                    payload, state = fetch_payload(url)
                    if payload is None:
                        if state == "missing":
                            files_missing += 1
                        continue
                    files_found += 1
                    for line in iter_zip_lines(payload):
                        open_ms = raw_open_time(line)
                        if open_ms is None or open_ms < start_ms or open_ms > end_ms:
                            continue
                        output.write(line)
                        candles += 1
                        if first_ms == "":
                            first_ms = str(open_ms)
                        last_ms = str(open_ms)

        if candles == 0:
            os.remove(tmp_path)
            return {
                "symbol": symbol,
                "status": "empty",
                "candles": 0,
                "start_ms": "",
                "end_ms": "",
                "files_found": files_found,
                "files_missing": files_missing,
                "path": out_path,
                "error": "",
            }

        os.replace(tmp_path, out_path)
        return {
            "symbol": symbol,
            "status": "ok" if files_missing == 0 else "partial",
            "candles": candles,
            "start_ms": first_ms,
            "end_ms": last_ms,
            "files_found": files_found,
            "files_missing": files_missing,
            "path": out_path,
            "error": "",
        }
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return {
            "symbol": symbol,
            "status": "error",
            "candles": candles,
            "start_ms": first_ms,
            "end_ms": last_ms,
            "files_found": files_found,
            "files_missing": files_missing,
            "path": out_path,
            "error": str(exc),
        }


def main():
    args = parse_args()
    if args.out_dir is None:
        args.out_dir = f"data/futures_{args.interval}_raw_history"
    if args.manifest is None:
        args.manifest = f"data/futures_{args.interval}_raw_history_manifest.csv"
    if args.report is None:
        args.report = f"strategies/futures-{args.interval}-raw-history-download.md"

    start_day = date.fromisoformat(args.start)
    end_day = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date() - timedelta(days=1)
    symbols = load_symbols(os.path.join(ROOT, args.symbols_file), args.limit)
    manifest_path = os.path.join(ROOT, args.manifest)
    report_path = os.path.join(ROOT, args.report)
    previous = existing_manifest(manifest_path)
    results = dict(previous)

    print(
        f"Fast downloading {len(symbols)} symbols {args.interval} raw from {start_day} to {end_day} "
        f"with {args.workers} workers",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_symbol, symbol, args, start_day, end_day, previous.get(symbol)): symbol
            for symbol in symbols
        }
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            results[row["symbol"]] = row
            if index % 10 == 0 or index == len(symbols):
                save_manifest(manifest_path, list(results.values()))
                print(f"[{index}/{len(symbols)}] {row['symbol']} {row['status']} candles={row['candles']}", flush=True)

    rows = [results[symbol] for symbol in symbols if symbol in results]
    save_manifest(manifest_path, rows)
    save_report(report_path, rows, args, start_day, end_day)
    print(f"Done. Manifest: {manifest_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
