#!/usr/bin/env python3
"""Check fixed RIF-like setup on higher candle intervals.

The original RIF regime scripts are 1m-specific. This script keeps the same
strategy idea but makes the bars-per-day math interval-aware, so 5m and 1h can
be tested honestly across 1/7/30/60/90/180/365 day windows.
"""

import argparse
import csv
import importlib.util
import io
import math
import os
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")

ARCHIVE_DAILY_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
ARCHIVE_MONTHLY_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
INITIAL_BALANCE = 1000.0

DEFAULT_SYMBOLS = ["RIFUSDT", "MOVRUSDT"]
DEFAULT_INTERVALS = ["5m", "1h"]
DEFAULT_PERIODS = [1, 7, 30, 60, 90, 180, 365]

FIXED_SPEC = {
    "coin": "",
    "symbol": "",
    "kind": "single",
    "direction": "long",
    "threshold": 50,
    "regime": "wide",
    "position_pct": 1.0,
    "tp_pct": 0.012,
    "sl_pct": 0.04,
    "time_stop_min": 90,
}

POLICIES = [
    {
        "policy": "always_on_base",
        "gate": "always",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60",
        "gate": "health30_60",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60_weekly_kill",
        "gate": "health30_60",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": 0.02,
    },
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def utc_ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def request_url(url, method="GET", retries=3):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "rif-interval-check/1.0"})
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                if method == "HEAD":
                    return b""
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


def archive_daily_url(symbol, interval, day):
    day_text = day.isoformat()
    return f"{ARCHIVE_DAILY_BASE}/{symbol}/{interval}/{symbol}-{interval}-{day_text}.zip"


def archive_monthly_url(symbol, interval, month):
    month_text = f"{month.year:04d}-{month.month:02d}"
    return f"{ARCHIVE_MONTHLY_BASE}/{symbol}/{interval}/{symbol}-{interval}-{month_text}.zip"


def url_exists(url):
    try:
        request_url(url, method="HEAD", retries=1)
        return True
    except FileNotFoundError:
        return False


def latest_archive_day(symbol, interval):
    today = datetime.now(timezone.utc).date()
    for offset in range(0, 14):
        candidate = today - timedelta(days=offset)
        if url_exists(archive_daily_url(symbol, interval, candidate)):
            return candidate
    raise RuntimeError(f"No recent futures archive files found for {symbol} {interval}")


def parse_zip_payload(payload):
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
                open_time = int(item[0])
                close_time = int(item[6])
                rows.append(
                    {
                        "open_time_ms": open_time,
                        "close_time_ms": close_time,
                        "open_time": utc_ms_to_iso(open_time),
                        "close_time": utc_ms_to_iso(close_time),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
    return rows


def fetch_zip_rows(url):
    try:
        return parse_zip_payload(request_url(url))
    except FileNotFoundError:
        return []


def first_day_of_month(value):
    return date(value.year, value.month, 1)


def next_month(value):
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def month_starts(start_day, end_day):
    current = first_day_of_month(start_day)
    end_month = first_day_of_month(end_day)
    while current <= end_month:
        yield current
        current = next_month(current)


def fetch_archive_klines(symbol, interval, days, archive_end_day=None):
    end_day = date.fromisoformat(archive_end_day) if archive_end_day else latest_archive_day(symbol, interval)
    start_day = end_day - timedelta(days=days - 1)
    start_dt = datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rows = []
    latest_month = first_day_of_month(end_day)
    for month in month_starts(start_day, end_day):
        month_end = next_month(month) - timedelta(days=1)
        if month < latest_month:
            monthly_rows = fetch_zip_rows(archive_monthly_url(symbol, interval, month))
            if monthly_rows:
                rows.extend(monthly_rows)
                continue

        day = max(month, start_day)
        final_day = min(month_end, end_day)
        while day <= final_day:
            rows.extend(fetch_zip_rows(archive_daily_url(symbol, interval, day)))
            day += timedelta(days=1)

    rows = [row for row in rows if start_ms <= row["open_time_ms"] <= end_ms]
    rows.sort(key=lambda row: row["open_time_ms"])
    deduped = []
    seen = set()
    for row in rows:
        if row["open_time_ms"] in seen:
            continue
        seen.add(row["open_time_ms"])
        deduped.append(row)
    return deduped, start_day, end_day


def coin_from_symbol(symbol):
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def fixed_spec(symbol):
    spec = dict(FIXED_SPEC)
    spec["symbol"] = symbol
    spec["coin"] = coin_from_symbol(symbol)
    return spec


def utc_day_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def daily_start_indices(candles):
    starts = []
    previous_day = None
    for index, row in enumerate(candles):
        day = utc_day_from_ms(row["open_time_ms"])
        if day != previous_day:
            starts.append((day, index))
            previous_day = day
    return starts


def make_args(rif, multi, reinvest, cf, spec, interval, policy):
    args = rif.make_args(
        multi,
        reinvest,
        cf,
        spec,
        position_pct=policy["position_pct"],
        daily_loss_stop_pct=policy["daily_loss_stop_pct"],
        weekly_loss_stop_pct=policy["weekly_loss_stop_pct"],
    )
    args.interval = interval
    args.market = "futures_archive"
    return args


def run_rows(bt, rif, multi, reinvest, cf, rows, spec, interval, policy):
    test_rows = [dict(row) for row in rows]
    cf.apply_single_signals(test_rows, spec["direction"], spec["threshold"], spec["regime"])
    args = make_args(rif, multi, reinvest, cf, spec, interval, policy)
    trades, equity, stats = bt.run_backtest(test_rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return summary, stats


def compute_health_cache(bt, rif, multi, reinvest, cf, candles, spec, interval, starts, target_start, windows):
    cache = {}
    per_day = bt.candles_per_day(interval)
    base_policy = POLICIES[0]
    for number, (day, index) in enumerate(starts, start=1):
        if index < target_start:
            continue
        cache[day] = {}
        for window in windows:
            bars = window * per_day
            if index < bars:
                continue
            rows = candles[index - bars : index]
            summary, _ = run_rows(bt, rif, multi, reinvest, cf, rows, spec, interval, base_policy)
            cache[day][window] = {
                "return_pct": summary["total_return_pct"],
                "profit_factor": summary["profit_factor"],
                "max_dd_pct": summary["max_drawdown_pct"],
                "trades": summary["total_trades"],
            }
        if number % 50 == 0:
            print(f"  health days computed through {day}", flush=True)
    return cache


def gate_target_rows(cf, candles, spec, active_days):
    rows = [dict(row) for row in candles]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    active = set(active_days)
    for row in rows:
        if utc_day_from_ms(row["open_time_ms"]) not in active:
            row["long_signal"] = False
            row["short_signal"] = False
    return rows


def run_policy(bt, rif, multi, reinvest, cf, candles, spec, interval, days, policy, health_cache):
    per_day = bt.candles_per_day(interval)
    target_bars = days * per_day
    target_rows = candles[-target_bars:]
    starts = daily_start_indices(target_rows)

    active_days = []
    gate_reasons = Counter()
    for day, _index in starts:
        passed, reason = rif.passes_gate(policy["gate"], health_cache.get(day, {}))
        gate_reasons[reason if passed else f"blocked:{reason}"] += 1
        if passed:
            active_days.append(day)

    if policy["gate"] == "always":
        active_days = [day for day, _index in starts]
        gate_reasons = Counter({"always_on": len(active_days)})

    rows = gate_target_rows(cf, target_rows, spec, active_days)
    args = make_args(rif, multi, reinvest, cf, spec, interval, policy)
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return {
        "symbol": spec["symbol"],
        "interval": interval,
        "policy": policy["policy"],
        "gate": policy["gate"],
        "period_days": days,
        "active_days": len(active_days),
        "inactive_days": len(starts) - len(active_days),
        "active_ratio_pct": len(active_days) / len(starts) * 100.0 if starts else 0.0,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "profit_factor": summary["profit_factor"],
        "win_rate_pct": summary["win_rate_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
        "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
        "gate_reasons": ";".join(f"{key}={value}" for key, value in gate_reasons.items()),
    }


def run_symbol_interval(bt, rif, reinvest, multi, cf, symbol, interval, periods, health_window, archive_end_day):
    max_period = max(periods)
    fetch_days = max_period + health_window
    candles, start_day, end_day = fetch_archive_klines(symbol, interval, fetch_days, archive_end_day)
    per_day = bt.candles_per_day(interval)
    if len(candles) < max_period * per_day:
        raise RuntimeError(f"not enough candles for {symbol} {interval}: {len(candles)}")

    spec = fixed_spec(symbol)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    indicator_args.interval = interval
    bt.add_indicators_and_signals(candles, indicator_args)
    print(
        f"{symbol} {interval}: candles={len(candles)} "
        f"start={candles[0]['open_time']} end={candles[-1]['close_time']}",
        flush=True,
    )

    target_start = len(candles) - max_period * per_day
    starts = daily_start_indices(candles)
    health_cache = compute_health_cache(
        bt,
        rif,
        multi,
        reinvest,
        cf,
        candles,
        spec,
        interval,
        starts,
        target_start,
        [30, 60, 90],
    )

    rows = []
    for period in periods:
        for policy in POLICIES:
            result = run_policy(bt, rif, multi, reinvest, cf, candles, spec, interval, period, policy, health_cache)
            result["data_start_day"] = start_day.isoformat()
            result["data_end_day"] = end_day.isoformat()
            rows.append(result)
            print(
                f"  {period}d {policy['policy']}: ret={result['return_pct']:+.2f}% "
                f"dd={result['max_dd_pct']:.2f}% pf={result['profit_factor']:.3f} "
                f"active={result['active_days']} trades={result['trades']}",
                flush=True,
            )
    return rows


def write_report(path, rows, periods, detail_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# RIF/MOVR Interval Windows Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker offset `0.05%`, maker fee `0.02%`, slippage `0`.",
        "Источник: Binance Futures archive. На 5m и 1h лимитный вход проверяется по касанию внутри следующей свечи выбранного таймфрейма.",
        "",
    ]
    for interval in sorted({row["interval"] for row in rows}, key=lambda value: ["5m", "1h"].index(value) if value in {"5m", "1h"} else value):
        for policy in ("health30_60", "health30_60_weekly_kill", "always_on_base"):
            selected = [row for row in rows if row["interval"] == interval and row["policy"] == policy]
            if not selected:
                continue
            by = {(row["symbol"], int(row["period_days"])): row for row in selected}
            symbols = sorted({row["symbol"] for row in selected})
            title = {
                "health30_60": "Main: health30_60",
                "health30_60_weekly_kill": "Defensive: health30_60_weekly_kill",
                "always_on_base": "Raw always-on reference",
            }[policy]
            lines.extend(
                [
                    f"## {interval} - {title}",
                    "",
                    "| Symbol | " + " | ".join(f"{period}d" for period in periods) + " | DD 365d | PF 365d |",
                    "|---|" + "---:|" * (len(periods) + 2),
                ]
            )
            for symbol in symbols:
                values = []
                for period in periods:
                    row = by.get((symbol, period))
                    values.append(fmt_pct(row["return_pct"]) if row else "n/a")
                row365 = by.get((symbol, 365))
                lines.append(
                    f"| `{symbol}` | "
                    + " | ".join(values)
                    + f" | {fmt_num(row365['max_dd_pct']) if row365 else 'n/a'}% | {fmt_num(row365['profit_factor']) if row365 else 'n/a'} |"
                )
            lines.append("")
    lines.extend(
        [
            "## Files",
            "",
            f"- Detail CSV: `{detail_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Check RIF-like setup on 5m/1h intervals.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--intervals", nargs="*", default=DEFAULT_INTERVALS, choices=["5m", "1h"])
    parser.add_argument("--periods", nargs="*", type=int, default=DEFAULT_PERIODS)
    parser.add_argument("--max-health-window", type=int, default=90)
    parser.add_argument("--archive-end-day", default="")
    parser.add_argument("--save-detail", default=f"data/rif_interval_windows_detail_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-interval-windows-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)

    rows = []
    for symbol in args.symbols:
        for interval in args.intervals:
            rows.extend(
                run_symbol_interval(
                    bt,
                    rif,
                    reinvest,
                    multi,
                    cf,
                    symbol,
                    interval,
                    args.periods,
                    args.max_health_window,
                    args.archive_end_day or None,
                )
            )

    fields = [
        "symbol",
        "interval",
        "policy",
        "gate",
        "period_days",
        "active_days",
        "inactive_days",
        "active_ratio_pct",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
        "gate_reasons",
        "data_start_day",
        "data_end_day",
    ]
    save_csv(os.path.join(ROOT, args.save_detail), rows, fields)
    write_report(args.save_report, rows, args.periods, args.save_detail)
    print(f"saved detail: {args.save_detail}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
