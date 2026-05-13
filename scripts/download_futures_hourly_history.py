#!/usr/bin/env python3
"""Download Binance USD-M futures candle history for a symbol universe.

The script uses the public data.binance.vision archive instead of the Binance
trading API, so it works even when the exchange API is region-blocked.
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
FIELDS = [
    "open_time",
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "close_time_ms",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Download Binance Futures candle history.")
    parser.add_argument("--symbols-file", default="data/binance_futures_active_usdt_ascii_symbols_2026-05-04.txt")
    parser.add_argument("--start", default="2023-01-01", help="UTC start date, YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="UTC end date, YYYY-MM-DD. Default: latest completed UTC day.")
    parser.add_argument("--interval", default="1h", choices=["1m", "5m", "15m", "1h", "4h"])
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Optional first N symbols for testing.")
    return parser.parse_args()


def utc_ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


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


def request_url(url, retries=3):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(url)
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def archive_url(base, symbol, interval, stamp):
    safe_symbol = urllib.parse.quote(symbol, safe="")
    return f"{base}/{safe_symbol}/{interval}/{safe_symbol}-{interval}-{stamp}.zip"


def monthly_url(symbol, interval, month):
    return archive_url(MONTHLY_BASE, symbol, interval, f"{month.year:04d}-{month.month:02d}")


def daily_url(symbol, interval, day):
    return archive_url(DAILY_BASE, symbol, interval, day.isoformat())


def parse_zip(payload):
    rows = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_names:
            return rows
        with archive.open(csv_names[0]) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8")
            reader = csv.reader(text)
            for item in reader:
                if not item or not item[0].isdigit():
                    continue
                open_time_ms = int(item[0])
                close_time_ms = int(item[6])
                rows.append(
                    {
                        "open_time": utc_ms_to_iso(open_time_ms),
                        "open_time_ms": open_time_ms,
                        "open": item[1],
                        "high": item[2],
                        "low": item[3],
                        "close": item[4],
                        "volume": item[5],
                        "close_time": utc_ms_to_iso(close_time_ms),
                        "close_time_ms": close_time_ms,
                        "quote_volume": item[7] if len(item) > 7 else "",
                        "trades": item[8] if len(item) > 8 else "",
                        "taker_buy_base_volume": item[9] if len(item) > 9 else "",
                        "taker_buy_quote_volume": item[10] if len(item) > 10 else "",
                    }
                )
    return rows


def fetch_rows(url):
    try:
        return parse_zip(request_url(url)), "ok"
    except FileNotFoundError:
        return [], "missing"


def load_symbols(path, limit=None):
    with open(path, encoding="utf-8") as handle:
        symbols = [line.strip().upper() for line in handle if line.strip()]
    symbols = [symbol for symbol in symbols if symbol.endswith("USDT") and "_" not in symbol]
    if limit:
        symbols = symbols[:limit]
    return symbols


def existing_manifest(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        rows = {}
        for row in csv.DictReader(handle):
            if row.get("status") == "skipped":
                try:
                    missing = int(row.get("files_missing") or 0)
                    candles = int(row.get("candles") or 0)
                except ValueError:
                    missing = 0
                    candles = 0
                if candles <= 0:
                    row["status"] = "empty"
                else:
                    row["status"] = "partial" if missing else "ok"
            rows[row["symbol"]] = row
        return rows


def save_manifest(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = [
        "symbol",
        "status",
        "candles",
        "start",
        "end",
        "files_found",
        "files_missing",
        "path",
        "error",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["symbol"]))


def save_report(path, rows, start_day, end_day, args):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok = [row for row in rows if row["status"] in ("ok", "skipped")]
    empty = [row for row in rows if row["status"] == "empty"]
    errors = [row for row in rows if row["status"] == "error"]
    partial = [row for row in rows if row["status"] == "partial"]
    total_candles = sum(int(row.get("candles") or 0) for row in ok + partial)
    lines = [
        f"# Binance Futures {args.interval} History Download",
        "",
        f"Period: `{start_day}` -> `{end_day}` UTC.",
        f"Symbols total: `{len(rows)}`.",
        f"OK/skipped: `{len(ok)}`.",
        f"Partial: `{len(partial)}`.",
        f"Empty/no history: `{len(empty)}`.",
        f"Errors: `{len(errors)}`.",
        f"Total candles saved: `{total_candles}`.",
        "",
        f"Output folder: `{args.out_dir}/`.",
        f"Manifest: `{args.manifest}`.",
        "",
    ]
    if partial:
        lines.extend(["## Partial Symbols", ""])
        for row in partial[:50]:
            lines.append(
                f"- `{row['symbol']}`: candles `{row['candles']}`, missing files `{row['files_missing']}`, "
                f"range `{row['start']}` -> `{row['end']}`"
            )
        lines.append("")
    if empty:
        lines.extend(["## Empty Symbols", ""])
        lines.append(", ".join(f"`{row['symbol']}`" for row in empty[:100]))
        lines.append("")
    if errors:
        lines.extend(["## Errors", ""])
        for row in errors[:50]:
            lines.append(f"- `{row['symbol']}`: {row['error']}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def target_complete(existing, out_path, overwrite):
    if overwrite or not os.path.exists(out_path):
        return False
    return existing.get("status") in ("ok", "partial") and os.path.getsize(out_path) > 0


def download_symbol(symbol, args, start_day, end_day, existing_row):
    out_path = os.path.join(args.out_dir, f"{symbol}_{args.interval}.csv")
    if target_complete(existing_row or {}, out_path, args.overwrite):
        return {
            "symbol": symbol,
            "status": existing_row.get("status", "ok"),
            "candles": existing_row.get("candles", "0"),
            "start": existing_row.get("start", ""),
            "end": existing_row.get("end", ""),
            "files_found": existing_row.get("files_found", ""),
            "files_missing": existing_row.get("files_missing", ""),
            "path": out_path,
            "error": "",
        }

    start_ms = int(datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)
    latest_month = first_day_of_month(end_day)
    rows = []
    files_found = 0
    files_missing = 0

    try:
        for month in month_starts(start_day, end_day):
            month_end = next_month(month) - timedelta(days=1)
            if month < latest_month:
                month_rows, state = fetch_rows(monthly_url(symbol, args.interval, month))
                if month_rows:
                    rows.extend(month_rows)
                    files_found += 1
                else:
                    files_missing += 1 if state == "missing" else 0
                continue

            day = max(month, start_day)
            final_day = min(month_end, end_day)
            while day <= final_day:
                day_rows, state = fetch_rows(daily_url(symbol, args.interval, day))
                if day_rows:
                    rows.extend(day_rows)
                    files_found += 1
                else:
                    files_missing += 1 if state == "missing" else 0
                day += timedelta(days=1)

        filtered = [row for row in rows if start_ms <= int(row["open_time_ms"]) <= end_ms]
        filtered.sort(key=lambda row: int(row["open_time_ms"]))
        deduped = []
        seen = set()
        for row in filtered:
            key = row["open_time_ms"]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)

        if not deduped:
            return {
                "symbol": symbol,
                "status": "empty",
                "candles": 0,
                "start": "",
                "end": "",
                "files_found": files_found,
                "files_missing": files_missing,
                "path": out_path,
                "error": "",
            }

        os.makedirs(args.out_dir, exist_ok=True)
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(deduped)
        os.replace(tmp_path, out_path)

        first = deduped[0]["open_time"]
        last = deduped[-1]["open_time"]
        status = "ok" if files_missing == 0 else "partial"
        return {
            "symbol": symbol,
            "status": status,
            "candles": len(deduped),
            "start": first,
            "end": last,
            "files_found": files_found,
            "files_missing": files_missing,
            "path": out_path,
            "error": "",
        }
    except Exception as exc:
        tmp_path = out_path + ".tmp"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return {
            "symbol": symbol,
            "status": "error",
            "candles": 0,
            "start": "",
            "end": "",
            "files_found": files_found,
            "files_missing": files_missing,
            "path": out_path,
            "error": str(exc),
        }


def main():
    args = parse_args()
    if args.out_dir is None:
        args.out_dir = f"data/futures_{args.interval}_history"
    if args.manifest is None:
        args.manifest = f"data/futures_{args.interval}_history_manifest.csv"
    if args.report is None:
        args.report = f"strategies/futures-{args.interval}-history-download.md"
    start_day = date.fromisoformat(args.start)
    end_day = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date() - timedelta(days=1)
    symbols = load_symbols(os.path.join(ROOT, args.symbols_file), args.limit)
    manifest_path = os.path.join(ROOT, args.manifest)
    report_path = os.path.join(ROOT, args.report)
    previous = existing_manifest(manifest_path)
    results = dict(previous)

    print(
        f"Downloading {len(symbols)} symbols {args.interval} from {start_day} to {end_day} "
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
                print(
                    f"[{index}/{len(symbols)}] {row['symbol']} {row['status']} candles={row['candles']}",
                    flush=True,
                )

    rows = [results[symbol] for symbol in symbols if symbol in results]
    save_manifest(manifest_path, rows)
    save_report(report_path, rows, start_day, end_day, args)
    print(f"Done. Manifest: {manifest_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
