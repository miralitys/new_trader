#!/usr/bin/env python3
"""Deep validation for the CHZ 1h SHORT candidate."""

import argparse
import csv
import importlib.util
import math
import os
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_FETCH_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
SCENARIOS = [
    {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0},
    {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0},
    {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005},
    {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0},
]
SPEC = {
    "strategy": "CHZ 1h SHORT Candidate",
    "symbol": "CHZUSDT",
    "interval": "1h",
    "variant": {
        "direction": "short",
        "threshold": 50,
        "regime": "base",
        "volume_multiplier": 1.5,
        "atr_min_pct": 0.0015,
        "atr_max_pct": 0.025,
        "tp_pct": 0.050,
        "sl_pct": 0.050,
        "time_stop_min": 1440,
        "weekly_loss_stop_pct": 0.02,
    },
}


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


def make_args(multi, reinvest, variant, symbol, interval, scenario):
    template = "10" if variant["direction"] == "long" else "7.3"
    args = multi.make_strategy_args(reinvest, template, symbol)
    args.symbol = symbol
    args.interval = interval
    args.direction = variant["direction"]
    args.position_pct = 1.0
    args.fee_pct = scenario["fee_pct"]
    args.slippage_pct = scenario["slippage_pct"]
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0005
    args.limit_entry_timeout_min = 1
    args.daily_loss_stop_pct = 0.02
    args.weekly_loss_stop_pct = variant["weekly_loss_stop_pct"]
    args.time_stop_min = variant["time_stop_min"]
    args.long_time_stop_min = variant["time_stop_min"] if variant["direction"] == "long" else None
    args.short_time_stop_min = variant["time_stop_min"] if variant["direction"] == "short" else None
    args.long_tp_pct = variant["tp_pct"]
    args.long_sl_pct = variant["sl_pct"]
    args.short_tp_pct = variant["tp_pct"]
    args.short_sl_pct = variant["sl_pct"]
    return args


def run_slice(bt, adapt, multi, reinvest, candles, period_rows, scenario):
    rows = [dict(row) for row in period_rows]
    adapt.apply_variant_signals(rows, SPEC["variant"])
    args = make_args(multi, reinvest, SPEC["variant"], SPEC["symbol"], SPEC["interval"], scenario)
    args.initial_balance = INITIAL_BALANCE
    trades, equity_curve, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity_curve)
    return summary, stats


def run_windows(bt, adapt, multi, reinvest, candles):
    rows = []
    per_day = bt.candles_per_day(SPEC["interval"])
    for scenario in SCENARIOS:
        for period in WINDOWS:
            bars = period * per_day
            if len(candles) < bars:
                continue
            summary, stats = run_slice(bt, adapt, multi, reinvest, candles, candles[-bars:], scenario)
            rows.append(
                {
                    "strategy": SPEC["strategy"],
                    "symbol": SPEC["symbol"],
                    "interval": SPEC["interval"],
                    "scenario": scenario["name"],
                    "period_days": period,
                    "trades": summary["total_trades"],
                    "return_pct": summary["total_return_pct"],
                    "max_dd_pct": summary["max_drawdown_pct"],
                    "profit_factor": summary["profit_factor"],
                    "win_rate_pct": summary["win_rate_pct"],
                    "expectancy_pct": summary["expectancy_pct"],
                    "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
                    "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
                }
            )
    return rows


def run_months(bt, adapt, multi, reinvest, candles, start_day, end_day):
    rows = []
    base = SCENARIOS[0]
    for month, month_start, month_end in iter_month_ranges(start_day, end_day):
        start_ms = day_start_ms(month_start)
        end_ms = day_end_ms(month_end)
        month_rows = [row for row in candles if start_ms <= row["open_time_ms"] <= end_ms]
        if len(month_rows) < 2:
            summary = {
                "total_trades": 0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "profit_factor": 0.0,
                "win_rate_pct": 0.0,
                "expectancy_pct": 0.0,
            }
            stats = {}
        else:
            summary, stats = run_slice(bt, adapt, multi, reinvest, candles, month_rows, base)
        rows.append(
            {
                "strategy": SPEC["strategy"],
                "symbol": SPEC["symbol"],
                "interval": SPEC["interval"],
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
            }
        )
    return rows


def by_scenario_period(rows):
    grouped = {}
    for row in rows:
        grouped[(row["scenario"], int(row["period_days"]))] = row
    return grouped


def write_report(path, window_rows, monthly_rows, data_start, data_end, save_windows, save_monthly):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    grouped = by_scenario_period(window_rows)
    lines = [
        "# CHZ 1h SHORT Deep Validation",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Data: `{data_start}` - `{data_end}` from Binance Futures archive.",
        "",
        "Strategy: `CHZUSDT 1h SHORT`, threshold `50`, base regime, TP `5%`, SL `5%`, time stop `1440m`, weekly kill `2%`, maker-limit offset `0.05%`.",
        "",
        "## Window Check",
        "",
        "| Scenario | 1d | 7d | 30d | 60d | 90d | 180d | 365d | 730d | DD730 | PF730 | Trades730 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in [item["name"] for item in SCENARIOS]:
        values = {period: grouped.get((scenario, period), {}) for period in WINDOWS}
        row730 = values.get(730, {})
        lines.append(
            f"| `{scenario}` | "
            f"{fmt_pct(values[1].get('return_pct'))} | {fmt_pct(values[7].get('return_pct'))} | "
            f"{fmt_pct(values[30].get('return_pct'))} | {fmt_pct(values[60].get('return_pct'))} | "
            f"{fmt_pct(values[90].get('return_pct'))} | {fmt_pct(values[180].get('return_pct'))} | "
            f"{fmt_pct(values[365].get('return_pct'))} | {fmt_pct(row730.get('return_pct'))} | "
            f"{fmt_pct(row730.get('max_dd_pct'), signed=False)} | {fmt_num(row730.get('profit_factor'))} | "
            f"{row730.get('trades', '')} |"
        )
    positives = sum(1 for row in monthly_rows if float(row["return_pct"]) > 0)
    negatives = sum(1 for row in monthly_rows if float(row["return_pct"]) < 0)
    zeroes = len(monthly_rows) - positives - negatives
    worst = min(monthly_rows, key=lambda row: float(row["return_pct"])) if monthly_rows else {}
    best = max(monthly_rows, key=lambda row: float(row["return_pct"])) if monthly_rows else {}
    lines.extend(
        [
            "",
            "## Monthly Breakdown",
            "",
            f"- Positive months: `{positives}/{len(monthly_rows)}`",
            f"- Negative months: `{negatives}/{len(monthly_rows)}`",
            f"- Flat months: `{zeroes}/{len(monthly_rows)}`",
            f"- Worst month: `{worst.get('month', '')}` `{fmt_pct(worst.get('return_pct'))}`",
            f"- Best month: `{best.get('month', '')}` `{fmt_pct(best.get('return_pct'))}`",
            "",
            "| Month | Trades | Return | MaxDD | PF | Win rate |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in monthly_rows:
        lines.append(
            f"| {row['month']} | {row['trades']} | {fmt_pct(row['return_pct'])} | "
            f"{fmt_pct(row['max_dd_pct'], signed=False)} | {fmt_num(row['profit_factor'])} | "
            f"{fmt_pct(row['win_rate_pct'], signed=False)} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Window CSV: `{save_windows}`",
            f"- Monthly CSV: `{save_monthly}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Deep validation for CHZ 1h SHORT candidate.")
    parser.add_argument("--archive-end-day", default="")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--save-windows", default=f"data/chz_1h_short_validation_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/chz_1h_short_validation_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/CHZ/chz-1h-short-validation-{today}.md")
    args = parser.parse_args()

    interval_fetch = load_module("rif_interval_windows_check", INTERVAL_FETCH_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    archive_end_day = args.archive_end_day or None
    fetch_days = args.days + args.warmup_days
    candles, data_start, data_end = interval_fetch.fetch_archive_klines(
        SPEC["symbol"], SPEC["interval"], fetch_days, archive_end_day
    )
    indicator_args = multi.make_strategy_args(reinvest, "7.3", SPEC["symbol"])
    indicator_args.interval = SPEC["interval"]
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)

    start_day = data_end - timedelta(days=args.days - 1)
    start_ms = day_start_ms(start_day)
    test_candles = [row for row in candles if row["open_time_ms"] >= start_ms]
    window_rows = run_windows(bt, adapt, multi, reinvest, test_candles)
    monthly_rows = run_months(bt, adapt, multi, reinvest, candles, start_day, data_end)

    window_fields = [
        "strategy",
        "symbol",
        "interval",
        "scenario",
        "period_days",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
    ]
    monthly_fields = [
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
    ]
    save_csv(os.path.join(ROOT, args.save_windows), window_rows, window_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(
        os.path.join(ROOT, args.save_report),
        window_rows,
        monthly_rows,
        data_start,
        data_end,
        args.save_windows,
        args.save_monthly,
    )
    print(f"data: {data_start}..{data_end} candles={len(candles)}")
    print(f"saved windows: {args.save_windows}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
