#!/usr/bin/env python3
"""Backtest wave setups after historical hot-scan events.

This is not a long-only "trade the whole year" validation. It simulates a
daily scanner:

1. At the end of each UTC day it sees only past candles.
2. If the symbol is hot, an event is created.
3. The already selected setup is traded only after that event for 7/14/30/60d.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
HOT_PATH = os.path.join(ROOT, "scripts", "hot_coin_wave_scanner.py")
DEEP_PATH = os.path.join(ROOT, "scripts", "deep_validate_hot_shortlist.py")
INITIAL_BALANCE = 1000.0


SCENARIOS = [
    {
        "scenario": "strict_maker",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_offset": 0.0005,
    },
    {
        "scenario": "taker_like",
        "fee_pct": 0.0004,
        "slippage_pct": 0.0002,
        "entry_mode": "next_open",
        "limit_offset": 0.0,
    },
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def as_int(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def spec_from_row(row):
    return {
        "coin": row.get("coin") or row["symbol"].replace("USDT", ""),
        "symbol": row["symbol"],
        "kind": "single",
        "direction": row["direction"],
        "threshold": as_int(row, "threshold"),
        "regime": row["regime"],
        "position_pct": 1.0,
        "tp_pct": as_float(row, "tp_pct"),
        "sl_pct": as_float(row, "sl_pct", 0.04),
        "time_stop_min": as_int(row, "time_stop_min"),
    }


def scenario_args(multi, reinvest, cf, spec, scenario):
    args = cf.make_single_args(multi, reinvest, spec)
    args.fee_pct = scenario["fee_pct"]
    args.slippage_pct = scenario["slippage_pct"]
    args.entry_mode = scenario["entry_mode"]
    args.limit_entry_offset_pct = scenario["limit_offset"]
    args.limit_entry_timeout_min = 1
    return args


def run_forward_window(bt, reinvest, multi, cf, rows, spec, scenario):
    if not rows:
        return None
    test_rows = [dict(row) for row in rows]
    cf.apply_single_signals(test_rows, spec["direction"], spec["threshold"], spec["regime"])
    args = scenario_args(multi, reinvest, cf, spec, scenario)
    trades, equity, _ = bt.run_backtest(test_rows, args)
    return bt.summarize_trades(trades, INITIAL_BALANCE, equity)


def utc_day_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def daily_anchor_indices(candles):
    anchors = []
    previous_day = None
    previous_index = None
    for index, row in enumerate(candles):
        day = utc_day_from_ms(row["open_time_ms"])
        if previous_day is not None and day != previous_day:
            anchors.append((previous_day, previous_index))
        previous_day = day
        previous_index = index
    if previous_day is not None:
        anchors.append((previous_day, previous_index))
    return anchors


def window_rows_by_index(candles, start_index, bars):
    if start_index >= len(candles):
        return []
    end_index = min(len(candles), start_index + bars)
    return candles[start_index:end_index]


def return_pct(rows):
    if not rows:
        return 0.0
    start = rows[0]["open"]
    end = rows[-1]["close"]
    return (end / start - 1.0) * 100.0 if start else 0.0


def range_pct(rows):
    if not rows:
        return 0.0
    high = max(row["high"] for row in rows)
    low = min(row["low"] for row in rows)
    return (high / low - 1.0) * 100.0 if low else 0.0


def fmt_pct(value):
    if value is None:
        return "n/a"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def fmt_num(value):
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return "inf" if math.isinf(value) else f"{value:.2f}"


def percentile(values, pct):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * pct
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return values[low]
    return values[low] * (high - rank) + values[high] * (rank - low)


def average(values):
    return sum(values) / len(values) if values else None


def positive_rate(values):
    return sum(1 for value in values if value > 0) / len(values) * 100.0 if values else None


def metric_lookup(rows, symbol, scenario, forward_days):
    return [
        row
        for row in rows
        if row["symbol"] == symbol
        and row["scenario"] == scenario
        and int(row["forward_days"]) == forward_days
        and str(row["valid"]) == "True"
    ]


def summarize_symbol(event_rows, source_row):
    symbol = source_row["symbol"]
    strict7 = [as_float(row, "return_pct") for row in metric_lookup(event_rows, symbol, "strict_maker", 7)]
    strict14 = [as_float(row, "return_pct") for row in metric_lookup(event_rows, symbol, "strict_maker", 14)]
    strict30 = [as_float(row, "return_pct") for row in metric_lookup(event_rows, symbol, "strict_maker", 30)]
    taker7 = [as_float(row, "return_pct") for row in metric_lookup(event_rows, symbol, "taker_like", 7)]
    taker14 = [as_float(row, "return_pct") for row in metric_lookup(event_rows, symbol, "taker_like", 14)]
    strict_dd30 = [as_float(row, "max_dd_pct") for row in metric_lookup(event_rows, symbol, "strict_maker", 30)]
    events = sorted({row["event_id"] for row in event_rows if row["symbol"] == symbol})
    event_count = len(events)

    if event_count >= 3 and (average(strict14) or 0) > 0 and (positive_rate(strict14) or 0) >= 60 and (average(taker7) or 0) > 0:
        decision = "wave_candidate"
    elif event_count >= 1 and (average(strict14) or 0) > 0 and (average(taker7) or 0) > 0:
        decision = "fresh_wave_watch"
    elif event_count >= 1 and (average(strict14) or 0) > 0:
        decision = "maker_only_wave"
    else:
        decision = "weak_wave"

    return {
        "symbol": symbol,
        "coin": source_row.get("coin") or symbol.replace("USDT", ""),
        "direction": source_row["direction"],
        "threshold": source_row["threshold"],
        "regime": source_row["regime"],
        "tp_pct": source_row["tp_pct"],
        "sl_pct": source_row["sl_pct"],
        "time_stop_min": source_row["time_stop_min"],
        "event_count": event_count,
        "decision": decision,
        "strict7_avg_return_pct": average(strict7),
        "strict7_positive_rate_pct": positive_rate(strict7),
        "strict14_avg_return_pct": average(strict14),
        "strict14_median_return_pct": percentile(strict14, 0.5),
        "strict14_positive_rate_pct": positive_rate(strict14),
        "strict30_avg_return_pct": average(strict30),
        "strict30_median_return_pct": percentile(strict30, 0.5),
        "strict30_positive_rate_pct": positive_rate(strict30),
        "strict30_worst_return_pct": min(strict30) if strict30 else None,
        "strict30_best_return_pct": max(strict30) if strict30 else None,
        "strict30_avg_dd_pct": average(strict_dd30),
        "strict30_worst_dd_pct": max(strict_dd30) if strict_dd30 else None,
        "taker7_avg_return_pct": average(taker7),
        "taker7_positive_rate_pct": positive_rate(taker7),
        "taker14_avg_return_pct": average(taker14),
        "taker14_positive_rate_pct": positive_rate(taker14),
    }


def save_report(path, summary_rows, event_rows, diagnostics):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    counts = Counter(row["decision"] for row in summary_rows)
    diag_counts = Counter(row["status"] for row in diagnostics)
    ranked = sorted(
        summary_rows,
        key=lambda row: (
            row["decision"] in ("wave_candidate", "fresh_wave_watch"),
            row["strict14_avg_return_pct"] if row["strict14_avg_return_pct"] is not None else -999,
            row["strict30_avg_return_pct"] if row["strict30_avg_return_pct"] is not None else -999,
        ),
        reverse=True,
    )

    lines = [
        "# Wave After Hot Backtest",
        "",
        "Это проверка не по принципу `торговать весь год`, а по принципу `scanner увидел hot-режим, что было дальше`.",
        "",
        "В каждом историческом дне scanner видел только прошлые свечи. После hot-сигнала стратегия включалась на будущие 7/14/30/60 дней.",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for key in ("wave_candidate", "fresh_wave_watch", "maker_only_wave", "weak_wave"):
        lines.append(f"| {key} | {counts[key]} |")

    lines.extend(["", "## Data Counts", "", "| Status | Count |", "|---|---:|"])
    for key, value in sorted(diag_counts.items()):
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Symbol Summary",
            "",
            "| Symbol | Decision | Events | Direction | Strict 14d avg | Strict 14d win | Strict 30d avg | Strict 30d worst | Taker 7d avg |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in ranked:
        lines.append(
            f"| `{row['symbol']}` | {row['decision']} | {row['event_count']} | {row['direction']} | "
            f"{fmt_pct(row['strict14_avg_return_pct'])} | {fmt_num(row['strict14_positive_rate_pct'])}% | "
            f"{fmt_pct(row['strict30_avg_return_pct'])} | {fmt_pct(row['strict30_worst_return_pct'])} | "
            f"{fmt_pct(row['taker7_avg_return_pct'])} |"
        )

    candidates = [row for row in ranked if row["decision"] in ("wave_candidate", "fresh_wave_watch")]
    lines.extend(
        [
            "",
            "## Best Wave Candidates",
            "",
            "| Symbol | Events | Strict 7d avg | Strict 14d avg | Strict 30d avg | Strict 30d DD avg/worst | Taker 7d avg |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in candidates[:25]:
        lines.append(
            f"| `{row['symbol']}` | {row['event_count']} | {fmt_pct(row['strict7_avg_return_pct'])} | "
            f"{fmt_pct(row['strict14_avg_return_pct'])} | {fmt_pct(row['strict30_avg_return_pct'])} | "
            f"{fmt_num(row['strict30_avg_dd_pct'])}% / {fmt_num(row['strict30_worst_dd_pct'])}% | "
            f"{fmt_pct(row['taker7_avg_return_pct'])} |"
        )

    latest_events = sorted(event_rows, key=lambda row: row["event_time"], reverse=True)
    lines.extend(
        [
            "",
            "## Latest Hot Events",
            "",
            "| Event Time | Symbol | Hot Score | Reasons | Scenario | Forward | Return | PF | DD | Trades |",
            "|---|---|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in latest_events[:40]:
        lines.append(
            f"| {row['event_time']} | `{row['symbol']}` | {fmt_num(row['hot_score'])} | {row['hot_reasons']} | "
            f"{row['scenario']} | {row['forward_days']} | {fmt_pct(row['return_pct'])} | "
            f"{fmt_num(row['profit_factor'])} | {fmt_num(row['max_dd_pct'])}% | {row['trades']} |"
        )

    errors = [row for row in diagnostics if row["status"] != "ok"]
    if errors:
        lines.extend(["", "## Errors", "", "| Symbol | Error |", "|---|---|"])
        for row in errors:
            lines.append(f"| `{row['symbol']}` | {row['error']} |")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Test forward returns after historical hot events.")
    parser.add_argument("--input", default="data/hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=60)
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--baseline-days", type=int, default=30)
    parser.add_argument("--min-hot-score", type=float, default=50.0)
    parser.add_argument("--min-quote-volume", type=float, default=500000.0)
    parser.add_argument("--cooldown-days", type=int, default=7)
    parser.add_argument("--forward-windows", nargs="*", type=int, default=[7, 14, 30, 60])
    parser.add_argument("--save-events", default="data/wave_after_hot_events_2026-05-04.csv")
    parser.add_argument("--save-summary", default="data/wave_after_hot_summary_2026-05-04.csv")
    parser.add_argument("--save-diagnostics", default="data/wave_after_hot_diagnostics_2026-05-04.csv")
    parser.add_argument("--save-report", default="strategies/wave-after-hot-backtest-2026-05-04.md")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    hot = load_module("hot_coin_wave_scanner", HOT_PATH)
    deep = load_module("deep_validate_hot_shortlist", DEEP_PATH)

    if args.archive_end_day:
        fixed_end_day = datetime.strptime(args.archive_end_day, "%Y-%m-%d").date()
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    source_rows = read_csv(os.path.join(ROOT, args.input))
    first_days = deep.load_inventory_first_days(os.path.join(ROOT, args.inventory))

    event_fields = [
        "event_id",
        "symbol",
        "coin",
        "event_time",
        "trade_start_time",
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "hot_score",
        "hot_reasons",
        "return_3d_pct",
        "return_7d_pct",
        "return_14d_pct",
        "range_7d_pct",
        "volume_ratio_7d",
        "forward_days",
        "scenario",
        "fee_pct",
        "slippage_pct",
        "entry_mode",
        "limit_offset",
        "underlying_return_pct",
        "underlying_range_pct",
        "valid",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "expectancy_pct",
        "final_equity",
        "error",
    ]
    summary_fields = [
        "symbol",
        "coin",
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "event_count",
        "decision",
        "strict7_avg_return_pct",
        "strict7_positive_rate_pct",
        "strict14_avg_return_pct",
        "strict14_median_return_pct",
        "strict14_positive_rate_pct",
        "strict30_avg_return_pct",
        "strict30_median_return_pct",
        "strict30_positive_rate_pct",
        "strict30_worst_return_pct",
        "strict30_best_return_pct",
        "strict30_avg_dd_pct",
        "strict30_worst_dd_pct",
        "taker7_avg_return_pct",
        "taker7_positive_rate_pct",
        "taker14_avg_return_pct",
        "taker14_positive_rate_pct",
    ]
    diagnostics_fields = ["symbol", "status", "error", "candles", "data_start", "data_end", "events"]

    events_path = os.path.join(ROOT, args.save_events)
    summary_path = os.path.join(ROOT, args.save_summary)
    diagnostics_path = os.path.join(ROOT, args.save_diagnostics)
    report_path = os.path.join(ROOT, args.save_report)

    event_rows = read_csv(events_path) if args.resume and os.path.exists(events_path) else []
    diagnostics = read_csv(diagnostics_path) if args.resume and os.path.exists(diagnostics_path) else []
    done = {row["symbol"] for row in diagnostics}

    for index, source_row in enumerate(source_rows, start=1):
        spec = spec_from_row(source_row)
        symbol = spec["symbol"]
        if symbol in done:
            print(f"[{index}/{len(source_rows)}] {symbol} skipped resume", flush=True)
            continue
        print(f"[{index}/{len(source_rows)}] {symbol} wave events", flush=True)
        symbol_event_count = 0
        try:
            candles, _, _ = deep.fetch_klines_bounded(multi, symbol, args.days, args.warmup_days, first_days.get(symbol))
            if len(candles) < (args.baseline_days + 14 + 7) * 1440:
                raise RuntimeError(f"not enough candles: {len(candles)}")
            base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
            bt.add_indicators_and_signals(candles, base_args)
            anchors = daily_anchor_indices(candles)
            last_event_day = None
            history_days = max(30, args.baseline_days + 14)
            history_bars = history_days * 1440
            max_forward_bars = max(args.forward_windows) * 1440

            for day, anchor_index in anchors:
                if anchor_index + 1 < history_bars:
                    continue
                if len(candles) - (anchor_index + 1) < min(args.forward_windows) * 1440:
                    continue
                if last_event_day is not None and (day - last_event_day).days < args.cooldown_days:
                    continue
                past = candles[anchor_index + 1 - history_bars : anchor_index + 1]
                metrics = hot.market_metrics(symbol, past, args.baseline_days)
                if not metrics["is_hot"] or float(metrics["hot_score"]) < args.min_hot_score:
                    continue
                if float(metrics["quote_volume_7d_avg"]) < args.min_quote_volume:
                    continue

                last_event_day = day
                symbol_event_count += 1
                event_id = f"{symbol}_{day.isoformat()}_{symbol_event_count}"
                trade_start = candles[anchor_index + 1]["open_time"] if anchor_index + 1 < len(candles) else ""

                for forward_days in args.forward_windows:
                    bars = forward_days * 1440
                    forward_rows = window_rows_by_index(candles, anchor_index + 1, bars)
                    valid_forward = len(forward_rows) >= bars
                    for scenario in SCENARIOS:
                        if valid_forward:
                            summary = run_forward_window(bt, reinvest, multi, cf, forward_rows, spec, scenario)
                            row = {
                                "valid": True,
                                "trades": summary["total_trades"],
                                "return_pct": summary["total_return_pct"],
                                "win_rate_pct": summary["win_rate_pct"],
                                "profit_factor": summary["profit_factor"],
                                "max_dd_pct": summary["max_drawdown_pct"],
                                "expectancy_pct": summary["expectancy_pct"],
                                "final_equity": summary["final_equity"],
                                "error": "",
                            }
                        else:
                            row = {
                                "valid": False,
                                "trades": "",
                                "return_pct": "",
                                "win_rate_pct": "",
                                "profit_factor": "",
                                "max_dd_pct": "",
                                "expectancy_pct": "",
                                "final_equity": "",
                                "error": f"not enough forward candles: {len(forward_rows)} < {bars}",
                            }
                        event_rows.append(
                            {
                                "event_id": event_id,
                                "symbol": symbol,
                                "coin": spec["coin"],
                                "event_time": day.isoformat(),
                                "trade_start_time": trade_start,
                                "direction": spec["direction"],
                                "threshold": spec["threshold"],
                                "regime": spec["regime"],
                                "tp_pct": spec["tp_pct"],
                                "sl_pct": spec["sl_pct"],
                                "time_stop_min": spec["time_stop_min"],
                                "hot_score": metrics["hot_score"],
                                "hot_reasons": metrics["hot_reasons"],
                                "return_3d_pct": metrics["return_3d_pct"],
                                "return_7d_pct": metrics["return_7d_pct"],
                                "return_14d_pct": metrics["return_14d_pct"],
                                "range_7d_pct": metrics["range_7d_pct"],
                                "volume_ratio_7d": metrics["volume_ratio_7d"],
                                "forward_days": forward_days,
                                "scenario": scenario["scenario"],
                                "fee_pct": scenario["fee_pct"],
                                "slippage_pct": scenario["slippage_pct"],
                                "entry_mode": scenario["entry_mode"],
                                "limit_offset": scenario["limit_offset"],
                                "underlying_return_pct": return_pct(forward_rows),
                                "underlying_range_pct": range_pct(forward_rows),
                                **row,
                            }
                        )

            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "ok",
                    "error": "",
                    "candles": len(candles),
                    "data_start": candles[0]["open_time"],
                    "data_end": candles[-1]["close_time"],
                    "events": symbol_event_count,
                }
            )
            print(f"  events={symbol_event_count}", flush=True)
        except Exception as exc:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "error",
                    "error": str(exc),
                    "candles": "",
                    "data_start": "",
                    "data_end": "",
                    "events": "",
                }
            )
            print(f"  error: {exc}", flush=True)

        summary_rows = [summarize_symbol(event_rows, row) for row in source_rows]
        save_csv(events_path, event_rows, event_fields)
        save_csv(summary_path, summary_rows, summary_fields)
        save_csv(diagnostics_path, diagnostics, diagnostics_fields)
        save_report(report_path, summary_rows, event_rows, diagnostics)

    summary_rows = [summarize_symbol(event_rows, row) for row in source_rows]
    save_csv(events_path, event_rows, event_fields)
    save_csv(summary_path, summary_rows, summary_fields)
    save_csv(diagnostics_path, diagnostics, diagnostics_fields)
    save_report(report_path, summary_rows, event_rows, diagnostics)
    print(f"saved events: {events_path}")
    print(f"saved summary: {summary_path}")
    print(f"saved diagnostics: {diagnostics_path}")
    print(f"saved report: {report_path}")


if __name__ == "__main__":
    main()
