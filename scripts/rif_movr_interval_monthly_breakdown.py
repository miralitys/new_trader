#!/usr/bin/env python3
"""Monthly breakdown for fixed RIF/MOVR interval adaptations."""

import argparse
import csv
import importlib.util
import math
import os
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0

STRATEGIES = [
    {
        "strategy": "RIF 5m LONG Best",
        "symbol": "RIFUSDT",
        "interval": "5m",
        "variant": {
            "direction": "long",
            "threshold": 40,
            "regime": "wide",
            "volume_multiplier": 1.5,
            "atr_min_pct": 0.0015,
            "atr_max_pct": 0.025,
            "tp_pct": 0.010,
            "sl_pct": 0.060,
            "time_stop_min": 180,
            "weekly_loss_stop_pct": 0.02,
        },
    },
    {
        "strategy": "MOVR 1h LONG Best",
        "symbol": "MOVRUSDT",
        "interval": "1h",
        "variant": {
            "direction": "long",
            "threshold": 60,
            "regime": "base",
            "volume_multiplier": 1.5,
            "atr_min_pct": 0.0015,
            "atr_max_pct": 0.050,
            "tp_pct": 0.050,
            "sl_pct": 0.080,
            "time_stop_min": 1440,
            "weekly_loss_stop_pct": 0.02,
        },
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


def fmt_pct(value, signed=True):
    if value in ("", None):
        return "n/a"
    value = float(value)
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def month_floor(day):
    return date(day.year, day.month, 1)


def next_month(day):
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def iter_month_ranges(start_day, end_day):
    current = month_floor(start_day)
    while current <= month_floor(end_day):
        month_start = max(current, start_day)
        month_end = min(next_month(current) - timedelta(days=1), end_day)
        yield current.strftime("%Y-%m"), month_start, month_end
        current = next_month(current)


def day_start_ms(day):
    return int(datetime.combine(day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)


def day_end_ms(day):
    return int(datetime.combine(day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)


def run_strategy_months(bt, interval_mod, adapt, reinvest, multi, spec, archive_end_day, days, warmup_days):
    end_day = date.fromisoformat(archive_end_day)
    start_day = end_day - timedelta(days=days - 1)
    fetch_days = days + warmup_days
    candles, data_start, data_end = interval_mod.fetch_archive_klines(
        spec["symbol"], spec["interval"], fetch_days, archive_end_day
    )
    indicator_args = multi.make_strategy_args(reinvest, "10", spec["symbol"])
    indicator_args.interval = spec["interval"]
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)
    adapt.apply_variant_signals(candles, spec["variant"])

    args = adapt.make_args(multi, reinvest, spec["variant"], spec["symbol"], spec["interval"])
    args.initial_balance = INITIAL_BALANCE

    output = []
    for month, month_start, month_end in iter_month_ranges(start_day, end_day):
        start_ms = day_start_ms(month_start)
        end_ms = day_end_ms(month_end)
        rows = [dict(row) for row in candles if start_ms <= row["open_time_ms"] <= end_ms]
        if len(rows) < 2:
            summary = {
                "total_trades": 0,
                "total_return_pct": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "expectancy_pct": 0.0,
            }
            stats = {}
        else:
            trades, equity_curve, stats = bt.run_backtest(rows, args)
            summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity_curve)
        output.append(
            {
                "strategy": spec["strategy"],
                "symbol": spec["symbol"],
                "interval": spec["interval"],
                "month": month,
                "range_start": month_start.isoformat(),
                "range_end": month_end.isoformat(),
                "trades": summary["total_trades"],
                "return_pct": summary["total_return_pct"],
                "max_dd_pct": summary["max_drawdown_pct"],
                "profit_factor": summary["profit_factor"],
                "win_rate_pct": summary["win_rate_pct"],
                "expectancy_pct": summary["expectancy_pct"],
                "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
                "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
                "data_start": data_start.isoformat(),
                "data_end": data_end.isoformat(),
            }
        )
    return output


def write_report(path, rows, csv_path, archive_end_day, days):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# RIF/MOVR Monthly Breakdown",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Window: last `{days}` days ending `{archive_end_day}` from Binance Futures archive.",
        "",
        "Method: each calendar month is tested independently from `$1000`, with compounding inside that month only. Execution is the fixed strategy execution: maker-limit offset `0.05%`, maker fee `0.02%`, slippage `0`.",
        "",
    ]
    for strategy in [item["strategy"] for item in STRATEGIES]:
        lines.extend(
            [
                f"## {strategy}",
                "",
                "| Month | Range | Trades | Return | MaxDD | PF | Win rate | Expectancy |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in rows:
            if row["strategy"] != strategy:
                continue
            lines.append(
                f"| {row['month']} | {row['range_start']} - {row['range_end']} | "
                f"{row['trades']} | {fmt_pct(row['return_pct'])} | {fmt_pct(row['max_dd_pct'], signed=False)} | "
                f"{fmt_num(row['profit_factor'])} | {fmt_pct(row['win_rate_pct'], signed=False)} | "
                f"{fmt_pct(row['expectancy_pct'])} |"
            )
        lines.append("")
    lines.extend(["## Files", "", f"- CSV: `{csv_path}`", ""])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Monthly returns for fixed RIF/MOVR interval strategies.")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--save", default=f"data/rif_movr_interval_monthly_breakdown_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-movr-interval-monthly-breakdown-{today}.md")
    args = parser.parse_args()

    interval_mod = load_module("rif_interval_windows_check", INTERVAL_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    rows = []
    for spec in STRATEGIES:
        rows.extend(
            run_strategy_months(
                bt, interval_mod, adapt, reinvest, multi, spec, args.archive_end_day, args.days, args.warmup_days
            )
        )

    fields = [
        "strategy",
        "symbol",
        "interval",
        "month",
        "range_start",
        "range_end",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
        "data_start",
        "data_end",
    ]
    save_csv(os.path.join(ROOT, args.save), rows, fields)
    write_report(os.path.join(ROOT, args.save_report), rows, args.save, args.archive_end_day, args.days)
    print(f"saved csv: {args.save}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
