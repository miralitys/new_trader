#!/usr/bin/env python3
"""Build RIF/MOVR higher-interval trade rows for cashflow portfolio tests."""

import argparse
import csv
import importlib.util
import os
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
BREAKDOWN_PATH = os.path.join(ROOT, "scripts", "rif_movr_interval_monthly_breakdown.py")
MOVR_MONTHLY_PATH = os.path.join(ROOT, "scripts", "movr_monthly_4pct_portfolio_search.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
MONTHLY_PATH = os.path.join(ROOT, "scripts", "rif_movr_monthly_positive_search.py")

INITIAL_BALANCE = 1000.0


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


def day_start_ms(day):
    return int(datetime.combine(day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)


def day_end_ms(day):
    return int(datetime.combine(day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)


def build_interval_trades(bt, interval_mod, adapt, reinvest, multi, spec, archive_end_day, days, warmup_days):
    end_day = date.fromisoformat(archive_end_day)
    start_day = end_day - timedelta(days=days - 1)
    candles, _, _ = interval_mod.fetch_archive_klines(spec["symbol"], spec["interval"], days + warmup_days, archive_end_day)
    indicator_args = multi.make_strategy_args(reinvest, "10", spec["symbol"])
    indicator_args.interval = spec["interval"]
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)
    rows = [dict(row) for row in candles if day_start_ms(start_day) <= row["open_time_ms"] <= day_end_ms(end_day)]
    adapt.apply_variant_signals(rows, spec["variant"])
    args = adapt.make_args(multi, reinvest, spec["variant"], spec["symbol"], spec["interval"])
    args.initial_balance = INITIAL_BALANCE
    trades, _, _ = bt.run_backtest(rows, args)

    coin = spec["symbol"].replace("USDT", "")
    output = []
    for trade in trades:
        output.append(
            {
                "coin": coin,
                "symbol": spec["symbol"],
                "strategy": spec["strategy"],
                "direction": trade.get("direction", spec["variant"]["direction"]),
                "module": spec["strategy"],
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "reason": trade["reason"],
                "raw_return_pct": float(trade["net_return_pct"]),
                "allocation": "",
                "portfolio_return_pct": "",
            }
        )
    return output


def main():
    parser = argparse.ArgumentParser(description="Build RIF/MOVR interval trades.")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=1096)
    parser.add_argument("--warmup-days", type=int, default=120)
    parser.add_argument("--base-trades", default="data/cashflow_portfolio_best_trades_35m.csv")
    parser.add_argument("--save", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    interval_mod = load_module("rif_interval_windows_check", INTERVAL_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    breakdown = load_module("rif_movr_interval_monthly_breakdown", BREAKDOWN_PATH)
    movr_monthly = load_module("movr_monthly_4pct_portfolio_search", MOVR_MONTHLY_PATH)
    monthly_mod = load_module("rif_movr_monthly_positive_search", MONTHLY_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    rows = []
    with open(os.path.join(ROOT, args.base_trades), newline="", encoding="utf-8") as handle:
        rows.extend(csv.DictReader(handle))

    for spec in breakdown.STRATEGIES:
        rows.extend(
            build_interval_trades(
                bt,
                interval_mod,
                adapt,
                reinvest,
                multi,
                spec,
                args.archive_end_day,
                args.days,
                args.warmup_days,
            )
        )

    monthly_movr = movr_monthly.build_movr_trades(
        bt,
        interval_mod,
        adapt,
        monthly_mod,
        reinvest,
        multi,
        args.archive_end_day,
        args.days,
        args.warmup_days,
    )
    for trade in monthly_movr:
        rows.append(
            {
                "coin": "MOVR_M",
                "symbol": "MOVRUSDT",
                "strategy": "MOVR 1h Monthly Protected",
                "direction": "",
                "module": "MOVR 1h Monthly Protected",
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "reason": trade["reason"],
                "raw_return_pct": trade["raw_return_pct"],
                "allocation": "",
                "portfolio_return_pct": "",
            }
        )

    rows.sort(key=lambda item: (item["exit_time"], item["entry_time"], item["coin"]))
    fields = [
        "coin",
        "symbol",
        "strategy",
        "direction",
        "module",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "allocation",
        "portfolio_return_pct",
    ]
    save_csv(os.path.join(ROOT, args.save), rows, fields)
    print(f"saved {args.save}: {len(rows)} rows")


if __name__ == "__main__":
    main()
