#!/usr/bin/env python3
"""Stress-check selected 5m/1h interval strategy candidates."""

import argparse
import csv
import importlib.util
import math
import os
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_SEARCH_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
INTERVAL_FETCH_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0
WINDOWS = [30, 60, 90, 180, 365]
SCENARIOS = [
    {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0},
    {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0},
    {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005},
    {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0},
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
    return f"{float(value):+.2f}%"


def fmt_num(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def parse_float(value):
    if value in ("", None):
        return None
    return float(value)


def row_to_variant(row):
    return {
        "direction": row["direction"],
        "threshold": int(float(row["threshold"])),
        "regime": row["regime"],
        "volume_multiplier": float(row["volume_multiplier"]),
        "atr_min_pct": 0.0015,
        "atr_max_pct": float(row["atr_max_pct"]),
        "tp_pct": float(row["tp_pct"]),
        "sl_pct": float(row["sl_pct"]),
        "time_stop_min": int(float(row["time_stop_min"])),
        "weekly_loss_stop_pct": parse_float(row.get("weekly_loss_stop_pct")),
    }


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


def run_window(bt, interval_search, multi, reinvest, candles, symbol, interval, variant, period, scenario):
    per_day = bt.candles_per_day(interval)
    bars = period * per_day
    rows = [dict(row) for row in candles[-bars:]]
    interval_search.apply_variant_signals(rows, variant)
    args = make_args(multi, reinvest, variant, symbol, interval, scenario)
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return {
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


def candidate_ok(row):
    periods = [30, 60, 90, 180, 365]
    positives = sum(float(row[f"return_{period}d"]) > 0 for period in periods)
    return (
        positives >= 5
        and float(row["dd_365d"]) <= 16.0
        and float(row["pf_365d"]) >= 1.50
        and int(float(row["trades_365d"])) >= 40
    )


def load_candidates(path, top):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = [row for row in rows if candidate_ok(row)]
    if len(selected) < top:
        seen = {(row["symbol"], row["interval"], row["variant_id"]) for row in selected}
        for row in rows:
            key = (row["symbol"], row["interval"], row["variant_id"])
            if key in seen:
                continue
            selected.append(row)
            seen.add(key)
            if len(selected) >= top:
                break
    return selected[:top]


def write_report(path, rows, source_path, summary_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Interval Candidate Stress Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Проверка top 5m/1h кандидатов с ухудшением комиссии и проскальзывания.",
        "",
        "| Symbol | TF | Direction | Variant | Scenario | 30d | 60d | 90d | 180d | 365d | DD365 | PF365 | Trades365 |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    grouped = {}
    for row in rows:
        key = (row["symbol"], row["interval"], row["direction"], row["variant_id"], row["scenario"])
        grouped.setdefault(key, {})[int(row["period_days"])] = row
    for (symbol, interval, direction, variant_id, scenario), period_map in grouped.items():
        row365 = period_map.get(365, {})
        lines.append(
            f"| `{symbol}` | {interval} | {direction} | `{variant_id}` | `{scenario}` | "
            f"{fmt_pct(period_map[30]['return_pct'])} | {fmt_pct(period_map[60]['return_pct'])} | "
            f"{fmt_pct(period_map[90]['return_pct'])} | {fmt_pct(period_map[180]['return_pct'])} | "
            f"{fmt_pct(period_map[365]['return_pct'])} | {fmt_num(row365.get('max_dd_pct', 0))}% | "
            f"{fmt_num(row365.get('profit_factor', 0))} | {row365.get('trades', '')} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Source best CSV: `{source_path}`",
            f"- Stress summary CSV: `{summary_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Stress-check selected interval candidates.")
    parser.add_argument("--source-best", default="data/next_strategy_5m_1h_best_2026-05-08.csv")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--save-summary", default=f"data/interval_candidate_stress_check_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/interval-candidate-stress-check-{today}.md")
    args = parser.parse_args()

    interval_search = load_module("rif_interval_adaptation_search", INTERVAL_SEARCH_PATH)
    interval_fetch = load_module("rif_interval_windows_check", INTERVAL_FETCH_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    source_path = os.path.join(ROOT, args.source_best)
    candidates = load_candidates(source_path, args.top)
    candles_cache = {}
    rows = []
    for candidate in candidates:
        symbol = candidate["symbol"]
        interval = candidate["interval"]
        cache_key = (symbol, interval)
        if cache_key not in candles_cache:
            fetch_days = 365 + args.warmup_days
            candles, _start_day, _end_day = interval_fetch.fetch_archive_klines(
                symbol,
                interval,
                fetch_days,
                args.archive_end_day or None,
            )
            indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
            indicator_args.interval = interval
            indicator_args.atr_max_pct = 0.050
            bt.add_indicators_and_signals(candles, indicator_args)
            candles_cache[cache_key] = candles
        candles = candles_cache[cache_key]
        variant = row_to_variant(candidate)
        for scenario in SCENARIOS:
            for period in WINDOWS:
                result = run_window(
                    bt,
                    interval_search,
                    multi,
                    reinvest,
                    candles,
                    symbol,
                    interval,
                    variant,
                    period,
                    scenario,
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "direction": variant["direction"],
                        "variant_id": candidate["variant_id"],
                        "scenario": scenario["name"],
                        **variant,
                        **result,
                    }
                )

    fields = [
        "symbol",
        "interval",
        "direction",
        "variant_id",
        "scenario",
        "threshold",
        "regime",
        "volume_multiplier",
        "atr_min_pct",
        "atr_max_pct",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "weekly_loss_stop_pct",
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
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields)
    write_report(os.path.join(ROOT, args.save_report), rows, args.source_best, args.save_summary)

    print(f"checked candidates: {len(candidates)}")
    print(f"saved summary: {args.save_summary}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
