#!/usr/bin/env python3
"""Run the fixed GALA Minutka strategies on a basket of other symbols.

This is a cross-market robustness check, not parameter optimization.
The strategies are copied exactly from the current GALA winners:

- Minutka 7.3: SHORT, fixed TP/SL.
- Minutka 10: LONG, fixed TP/SL.
- Minutka 11.2: one-open-position portfolio of 10 + 7.3 x1.5.
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
BACKTEST_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")

DEFAULT_COINS = [
    "DOGE",
    "SHIB",
    "PEPE",
    "FLOKI",
    "BONK",
    "JASMY",
    "CHZ",
    "ALPINE",
    "SAND",
    "MANA",
    "APE",
    "ENJ",
    "IOTX",
    "ANKR",
    "AMP",
    "SPELL",
    "LRC",
    "COTI",
    "ZIL",
    "ONE",
]

WINDOWS = [7, 30, 60, 90, 180, 365]
ARCHIVE_DAILY_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
ARCHIVE_MONTHLY_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
INTERVAL = "1m"
INITIAL_BALANCE = 1000.0

SYMBOL_CANDIDATES = {
    "SHIB": ["1000SHIBUSDT", "SHIBUSDT"],
    "PEPE": ["1000PEPEUSDT", "PEPEUSDT"],
    "FLOKI": ["1000FLOKIUSDT", "FLOKIUSDT"],
    "BONK": ["1000BONKUSDT", "BONKUSDT"],
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc_ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def request_url(url, method="GET", retries=3):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "multi-coin-check/1.0"})
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


def archive_daily_url(symbol, day):
    day_text = day.isoformat()
    return f"{ARCHIVE_DAILY_BASE}/{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{day_text}.zip"


def archive_monthly_url(symbol, month):
    month_text = f"{month.year:04d}-{month.month:02d}"
    return f"{ARCHIVE_MONTHLY_BASE}/{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{month_text}.zip"


def url_exists(url):
    try:
        request_url(url, method="HEAD", retries=1)
        return True
    except FileNotFoundError:
        return False


def latest_archive_day(symbol):
    today = datetime.now(timezone.utc).date()
    for offset in range(0, 12):
        candidate = today - timedelta(days=offset)
        if url_exists(archive_daily_url(symbol, candidate)):
            return candidate
    raise RuntimeError(f"No recent futures archive files found for {symbol}")


def resolve_symbol(coin):
    candidates = SYMBOL_CANDIDATES.get(coin, [f"{coin}USDT"])
    errors = []
    for symbol in candidates:
        try:
            latest_archive_day(symbol)
            return symbol
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
    raise RuntimeError("; ".join(errors))


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


def fetch_klines_fast(symbol, days, warmup_days):
    end_day = latest_archive_day(symbol)
    total_days = days + warmup_days
    start_day = end_day - timedelta(days=total_days - 1)
    start_dt = datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rows = []
    latest_month = first_day_of_month(end_day)
    for month in month_starts(start_day, end_day):
        month_end = next_month(month) - timedelta(days=1)
        if month < latest_month:
            monthly_rows = fetch_zip_rows(archive_monthly_url(symbol, month))
            if monthly_rows:
                rows.extend(monthly_rows)
                continue

        day = max(month, start_day)
        final_day = min(month_end, end_day)
        while day <= final_day:
            rows.extend(fetch_zip_rows(archive_daily_url(symbol, day)))
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


def apply_strategy_signals(rows, strategy):
    for row in rows:
        if strategy == "7.3":
            row["long_signal"] = False
            row["short_signal"] = row.get("short_score", 0.0) >= 40 and bool(row.get("regime_filter_passed"))
        elif strategy == "10":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= 50
                and bool(row.get("smart_long_filter"))
                and bool(row.get("regime_filter_passed"))
            )
            row["short_signal"] = False
        else:
            raise ValueError(strategy)


def make_strategy_args(reinvest, strategy, symbol):
    internal = "minutka_7_3" if strategy == "7.3" else "minutka_10"
    args = reinvest.make_args(internal, INITIAL_BALANCE)
    args.symbol = symbol
    args.days = 365
    args.warmup_days = 7
    return args


def max_drawdown(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]["equity"]
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def summarize_portfolio(trades, equity_curve):
    wins = [trade for trade in trades if trade["risk_pnl"] > 0]
    losses = [trade for trade in trades if trade["risk_pnl"] < 0]
    gross_wins = sum(trade["risk_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["risk_pnl"] for trade in losses))
    returns = [trade["risk_return_pct"] for trade in trades]
    winning_returns = [value for value in returns if value > 0]
    losing_returns = [value for value in returns if value < 0]
    final_equity = equity_curve[-1]["equity"] if equity_curve else INITIAL_BALANCE
    return {
        "total_trades": len(trades),
        "total_return_pct": (final_equity / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "exit_reasons": Counter(trade["reason"] for trade in trades),
        "final_equity": final_equity,
    }


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_112_portfolio(short_trades, long_trades):
    source = []
    for trade in short_trades:
        item = dict(trade)
        item["module"] = "7.3 short x1.5"
        item["portfolio_weight"] = 1.5
        source.append(item)
    for trade in long_trades:
        item = dict(trade)
        item["module"] = "10 long"
        item["portfolio_weight"] = 1.0
        source.append(item)

    selected = []
    open_trades = []
    equity = INITIAL_BALANCE
    equity_curve = [{"time": "initial", "equity": equity}]
    for trade in sorted(source, key=lambda item: (parse_time(item["entry_time"]), parse_time(item["exit_time"]))):
        entry_dt = parse_time(trade["entry_time"])
        open_trades = [item for item in open_trades if parse_time(item["exit_time"]) > entry_dt]
        if open_trades:
            continue

        adjusted_return_pct = trade["net_return_pct"] * 0.9 * trade["portfolio_weight"]
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl
        output = dict(trade)
        output["risk_layer"] = "max_open_1_compound"
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})
    return selected, equity_curve, summarize_portfolio(selected, equity_curve)


def summary_row(coin, symbol, strategy, period, summary, data_start, data_end, candles_count):
    reasons = summary.get("exit_reasons", Counter())
    return {
        "coin": coin,
        "symbol": symbol,
        "strategy": strategy,
        "period": f"{period}d",
        "candles": candles_count,
        "data_start": data_start,
        "data_end": data_end,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "avg_win_pct": summary.get("avg_win_pct", 0.0),
        "avg_loss_pct": summary.get("avg_loss_pct", 0.0),
        "expectancy_pct": summary.get("expectancy_pct", 0.0),
        "final_equity": summary["final_equity"],
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "end_of_data": reasons["end_of_data"],
        "status": "ok",
        "error": "",
    }


def error_rows(coin, symbol, error):
    return [
        {
            "coin": coin,
            "symbol": symbol,
            "strategy": strategy,
            "period": f"{period}d",
            "candles": 0,
            "data_start": "",
            "data_end": "",
            "trades": 0,
            "return_pct": 0,
            "win_rate_pct": 0,
            "profit_factor": 0,
            "max_dd_pct": 0,
            "avg_win_pct": 0,
            "avg_loss_pct": 0,
            "expectancy_pct": 0,
            "final_equity": INITIAL_BALANCE,
            "take_profit": 0,
            "stop_loss": 0,
            "time_stop": 0,
            "end_of_data": 0,
            "status": "error",
            "error": str(error),
        }
        for strategy in ("7.3", "10", "11.2")
        for period in WINDOWS
    ]


def period_error_rows(coin, symbol, period, error, candles_count=0, data_start="", data_end=""):
    return [
        {
            "coin": coin,
            "symbol": symbol,
            "strategy": strategy,
            "period": f"{period}d",
            "candles": candles_count,
            "data_start": data_start,
            "data_end": data_end,
            "trades": 0,
            "return_pct": 0,
            "win_rate_pct": 0,
            "profit_factor": 0,
            "max_dd_pct": 0,
            "avg_win_pct": 0,
            "avg_loss_pct": 0,
            "expectancy_pct": 0,
            "final_equity": INITIAL_BALANCE,
            "take_profit": 0,
            "stop_loss": 0,
            "time_stop": 0,
            "end_of_data": 0,
            "status": "error",
            "error": str(error),
        }
        for strategy in ("7.3", "10", "11.2")
    ]


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_coin_readme(coin, rows):
    path = os.path.join(ROOT, "strategies", coin, "README.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok_rows = [row for row in rows if row["status"] == "ok"]
    lines = [
        f"# {coin} strategy check",
        "",
        "Проверка трех GALA-шаблонов на этой монете без оптимизации параметров.",
        "",
        "| Strategy | Period | Trades | Return | Win | PF | MaxDD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ok_rows:
        pf = row["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.2f}"
        lines.append(
            f"| {row['strategy']} | {row['period']} | {row['trades']} | "
            f"{row['return_pct']:+.2f}% | {row['win_rate_pct']:.2f}% | "
            f"{pf_text} | {row['max_dd_pct']:.2f}% |"
        )
    if not ok_rows:
        errors = sorted({row["error"] for row in rows if row["error"]})
        lines.extend(["", "Не удалось выполнить проверку:", ""])
        lines.extend(f"- {error}" for error in errors)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def copy_strategy_templates(coins):
    source_dir = os.path.join(ROOT, "strategies", "GALA")
    for coin in coins:
        target_dir = os.path.join(ROOT, "strategies", coin)
        os.makedirs(target_dir, exist_ok=True)
        for filename in ("minutka-7-3.md", "minutka-10.md", "minutka-11-2.md"):
            source = os.path.join(source_dir, filename)
            target = os.path.join(target_dir, filename)
            with open(source, encoding="utf-8") as handle:
                text = handle.read()
            text = text.replace("GALAUSDT", f"{coin}USDT")
            text = text.replace("GALA", coin)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)


def run_coin(bt, reinvest, coin, max_days, warmup_days):
    symbol = resolve_symbol(coin)
    candles, _, _ = fetch_klines_fast(symbol, max_days, warmup_days)
    if not candles:
        raise RuntimeError(f"No candles downloaded for {symbol}")

    indicator_args = make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    data_start = candles[0]["open_time"]
    data_end = candles[-1]["close_time"]
    rows = []

    for period in WINDOWS:
        needed = period * bt.candles_per_day(INTERVAL)
        if len(candles) < needed:
            rows.extend(
                period_error_rows(
                    coin,
                    symbol,
                    period,
                    f"Not enough candles for {period}d: {len(candles)} < {needed}",
                    len(candles),
                    data_start,
                    data_end,
                )
            )
            continue

        window_base = candles[-needed:]
        short_window = [dict(row) for row in window_base]
        long_window = [dict(row) for row in window_base]

        short_args = make_strategy_args(reinvest, "7.3", symbol)
        long_args = make_strategy_args(reinvest, "10", symbol)
        apply_strategy_signals(short_window, "7.3")
        apply_strategy_signals(long_window, "10")

        short_trades, short_equity, _ = bt.run_backtest(short_window, short_args)
        short_summary = bt.summarize_trades(short_trades, INITIAL_BALANCE, short_equity)
        rows.append(
            summary_row(coin, symbol, "7.3", period, short_summary, data_start, data_end, len(candles))
        )

        long_trades, long_equity, _ = bt.run_backtest(long_window, long_args)
        long_summary = bt.summarize_trades(long_trades, INITIAL_BALANCE, long_equity)
        rows.append(summary_row(coin, symbol, "10", period, long_summary, data_start, data_end, len(candles)))

        portfolio_trades, portfolio_equity, portfolio_summary = build_112_portfolio(
            short_trades, long_trades
        )
        rows.append(
            summary_row(
                coin,
                symbol,
                "11.2",
                period,
                portfolio_summary,
                data_start,
                data_end,
                len(candles),
            )
        )

    return rows


def main():
    parser = argparse.ArgumentParser(description="Run GALA strategy templates on other coins.")
    parser.add_argument("--coins", nargs="*", default=DEFAULT_COINS)
    parser.add_argument("--max-days", type=int, default=365)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument("--save-summary", default="data/multi_coin_gala_strategy_summary.csv")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BACKTEST_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    coins = [coin.upper() for coin in args.coins]
    copy_strategy_templates(coins)

    fields = [
        "coin",
        "symbol",
        "strategy",
        "period",
        "candles",
        "data_start",
        "data_end",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "avg_win_pct",
        "avg_loss_pct",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
        "end_of_data",
        "status",
        "error",
    ]

    all_rows = []
    for index, coin in enumerate(coins, start=1):
        print(f"[{index}/{len(coins)}] {coin}: running...")
        try:
            rows = run_coin(bt, reinvest, coin, args.max_days, args.warmup_days)
            all_rows.extend(rows)
            save_coin_readme(coin, rows)
            best = max(rows, key=lambda row: row["return_pct"])
            print(
                f"[{index}/{len(coins)}] {coin}: done, "
                f"best={best['strategy']} {best['period']} {best['return_pct']:+.2f}% "
                f"DD={best['max_dd_pct']:.2f}%"
            )
        except Exception as exc:
            symbol = SYMBOL_CANDIDATES.get(coin, [f"{coin}USDT"])[0]
            rows = error_rows(coin, symbol, exc)
            all_rows.extend(rows)
            save_coin_readme(coin, rows)
            print(f"[{index}/{len(coins)}] {coin}: ERROR {exc}")
        save_csv(os.path.join(ROOT, args.save_summary), all_rows, fields)

    print(f"saved summary: {args.save_summary}")


if __name__ == "__main__":
    main()
