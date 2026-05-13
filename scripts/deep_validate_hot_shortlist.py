#!/usr/bin/env python3
"""Deep validation for the Binance-wide hot shortlist.

The hot scanner finds current candidates on a short window. This script takes
those exact setups and validates them across larger windows and execution
scenarios, one symbol at a time, with checkpointed CSV outputs.
"""

import argparse
import csv
import importlib.util
import math
import os
import time
from collections import Counter, defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
INITIAL_BALANCE = 1000.0


SCENARIOS = [
    {
        "scenario": "base_maker",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_offset": 0.0,
    },
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


def load_inventory_first_days(path):
    if not path or not os.path.exists(path):
        return {}
    first_days = {}
    for row in read_csv(path):
        first_month = row.get("first_month")
        symbol = row.get("symbol")
        if not symbol or not first_month:
            continue
        try:
            first_days[symbol] = date.fromisoformat(f"{first_month}-01")
        except ValueError:
            continue
    return first_days


def fetch_klines_bounded(multi, symbol, days, warmup_days, first_day=None):
    end_day = multi.latest_archive_day(symbol)
    total_days = days + warmup_days
    start_day = end_day - timedelta(days=total_days - 1)
    if first_day is not None and first_day > start_day:
        start_day = first_day

    start_dt = datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rows = []
    latest_month = multi.first_day_of_month(end_day)
    for month in multi.month_starts(start_day, end_day):
        month_end = multi.next_month(month) - timedelta(days=1)
        if month < latest_month:
            monthly_rows = multi.fetch_zip_rows(multi.archive_monthly_url(symbol, month))
            if monthly_rows:
                rows.extend(monthly_rows)
                continue

        day = max(month, start_day)
        final_day = min(month_end, end_day)
        while day <= final_day:
            rows.extend(multi.fetch_zip_rows(multi.archive_daily_url(symbol, day)))
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


def run_one_window(bt, reinvest, multi, cf, candles, spec, period_days, scenario):
    bars = period_days * 1440
    if len(candles) < bars:
        return {
            "valid": False,
            "error": f"not enough candles: {len(candles)} < {bars}",
        }
    rows = [dict(row) for row in candles[-bars:]]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = scenario_args(multi, reinvest, cf, spec, scenario)
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    reasons = summary.get("exit_reasons", {})
    return {
        "valid": True,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "avg_win_pct": summary["avg_win_pct"],
        "avg_loss_pct": summary["avg_loss_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "final_equity": summary["final_equity"],
        "take_profit": reasons.get("take_profit", 0),
        "stop_loss": reasons.get("stop_loss", 0),
        "time_stop": reasons.get("time_stop", 0),
        "end_of_data": reasons.get("end_of_data", 0),
        "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
        "error": "",
    }


def metric_row(source_row, spec, period_days, scenario, result, data_start, data_end, available_days):
    row = {
        "symbol": spec["symbol"],
        "coin": spec["coin"],
        "direction": spec["direction"],
        "threshold": spec["threshold"],
        "regime": spec["regime"],
        "tp_pct": spec["tp_pct"],
        "sl_pct": spec["sl_pct"],
        "time_stop_min": spec["time_stop_min"],
        "period_days": period_days,
        "scenario": scenario["scenario"],
        "fee_pct": scenario["fee_pct"],
        "slippage_pct": scenario["slippage_pct"],
        "entry_mode": scenario["entry_mode"],
        "limit_offset": scenario["limit_offset"],
        "data_start": data_start,
        "data_end": data_end,
        "available_days": available_days,
        "hot_score": source_row.get("hot_score", ""),
        "hot_reasons": source_row.get("hot_reasons", ""),
        "valid": result.get("valid", False),
        "error": result.get("error", ""),
    }
    for key in (
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
        "daily_loss_stop_events",
    ):
        row[key] = result.get(key, "")
    return row


def fmt_pct(value):
    if value is None:
        return "n/a"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def fmt_pf(value):
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return "inf" if math.isinf(value) else f"{value:.2f}"


def best_metric(metrics, symbol, scenario, period):
    for row in metrics:
        if row["symbol"] == symbol and row["scenario"] == scenario and int(row["period_days"]) == period and str(row["valid"]) == "True":
            return row
    return None


def classify_symbol(metrics, symbol):
    strict30 = best_metric(metrics, symbol, "strict_maker", 30)
    strict90 = best_metric(metrics, symbol, "strict_maker", 90)
    strict365 = best_metric(metrics, symbol, "strict_maker", 365)
    strict730 = best_metric(metrics, symbol, "strict_maker", 730)
    taker30 = best_metric(metrics, symbol, "taker_like", 30)

    if strict365 and as_float(strict365, "return_pct") > 0 and as_float(strict365, "profit_factor") >= 1.05:
        if strict730 and as_float(strict730, "return_pct") > 0 and as_float(strict730, "profit_factor") >= 1.03:
            return "deep_pass_730"
        return "deep_pass_365"
    if strict90 and as_float(strict90, "return_pct") > 0 and strict30 and as_float(strict30, "return_pct") > 0:
        if taker30 and as_float(taker30, "return_pct") > 0:
            return "fresh_watch"
        return "maker_only_watch"
    return "reject_or_too_early"


def save_report(path, source_rows, metrics, diagnostics, periods):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    symbols = [row["symbol"] for row in source_rows]
    counts = Counter(classify_symbol(metrics, symbol) for symbol in symbols)
    diag_counts = Counter(row["status"] for row in diagnostics)

    strict_rows = [
        row
        for row in metrics
        if row["scenario"] == "strict_maker" and str(row["valid"]) == "True"
    ]
    top30 = sorted(
        [row for row in strict_rows if int(row["period_days"]) == 30],
        key=lambda row: as_float(row, "return_pct"),
        reverse=True,
    )
    top365 = sorted(
        [row for row in strict_rows if int(row["period_days"]) == 365],
        key=lambda row: as_float(row, "return_pct"),
        reverse=True,
    )

    lines = [
        "# Deep Validation: Binance Hot Shortlist",
        "",
        "Проверка берет **ровно тот setup**, который нашел быстрый Binance-wide hot-scan, и гонит его на больших окнах.",
        "",
        "Сценарии:",
        "",
        "- `base_maker`: maker 0.02%, лимит у текущей цены.",
        "- `strict_maker`: maker 0.02%, лимитка засчитывается только после возврата цены на 0.05%.",
        "- `taker_like`: fee 0.04% + slippage 0.02%, вход по следующему open.",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for key in ("deep_pass_730", "deep_pass_365", "fresh_watch", "maker_only_watch", "reject_or_too_early"):
        lines.append(f"| {key} | {counts[key]} |")

    lines.extend(
        [
            "",
            "## Data Counts",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]
    )
    for key, value in sorted(diag_counts.items()):
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Per-Symbol Summary",
            "",
            "| Symbol | Class | Strict 30d | Strict 90d | Strict 180d | Strict 365d | Strict 730d | Taker 30d |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for symbol in symbols:
        cls = classify_symbol(metrics, symbol)
        values = {}
        for period in (30, 90, 180, 365, 730):
            row = best_metric(metrics, symbol, "strict_maker", period)
            values[period] = fmt_pct(row["return_pct"]) + f" / PF {fmt_pf(row['profit_factor'])}" if row else "n/a"
        taker30 = best_metric(metrics, symbol, "taker_like", 30)
        taker30_text = fmt_pct(taker30["return_pct"]) if taker30 else "n/a"
        lines.append(
            f"| `{symbol}` | {cls} | {values[30]} | {values[90]} | {values[180]} | "
            f"{values[365]} | {values[730]} | {taker30_text} |"
        )

    lines.extend(
        [
            "",
            "## Top Strict 30d",
            "",
            "| Symbol | Direction | Period | Return | PF | DD | Trades |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top30[:25]:
        lines.append(
            f"| `{row['symbol']}` | {row['direction']} | {row['period_days']} | "
            f"{fmt_pct(row['return_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{float(row['max_dd_pct']):.2f}% | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Top Strict 365d",
            "",
            "| Symbol | Direction | Period | Return | PF | DD | Trades |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top365[:25]:
        lines.append(
            f"| `{row['symbol']}` | {row['direction']} | {row['period_days']} | "
            f"{fmt_pct(row['return_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{float(row['max_dd_pct']):.2f}% | {row['trades']} |"
        )

    errors = [row for row in diagnostics if row["status"] != "ok"]
    if errors:
        lines.extend(["", "## Errors", "", "| Symbol | Error |", "|---|---|"])
        for row in errors:
            lines.append(f"| `{row['symbol']}` | {row['error']} |")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Deep-validate hot Binance shortlist.")
    parser.add_argument("--input", default="data/hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv")
    parser.add_argument("--windows", nargs="*", type=int, default=[30, 60, 90, 180, 365, 730])
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--save-metrics", default="data/deep_hot_shortlist_metrics_2026-05-04.csv")
    parser.add_argument("--save-diagnostics", default="data/deep_hot_shortlist_diagnostics_2026-05-04.csv")
    parser.add_argument("--save-report", default="strategies/deep-hot-shortlist-validation-2026-05-04.md")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)

    if args.archive_end_day:
        fixed_end_day = date.fromisoformat(args.archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    input_path = os.path.join(ROOT, args.input)
    source_rows = read_csv(input_path)
    inventory_path = os.path.join(ROOT, args.inventory) if args.inventory else ""
    first_days = load_inventory_first_days(inventory_path)
    max_days = max(args.windows)
    fetch_days = max_days + args.warmup_days

    metric_fields = [
        "symbol",
        "coin",
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "period_days",
        "scenario",
        "fee_pct",
        "slippage_pct",
        "entry_mode",
        "limit_offset",
        "data_start",
        "data_end",
        "available_days",
        "hot_score",
        "hot_reasons",
        "valid",
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
        "daily_loss_stop_events",
        "error",
    ]
    diagnostics_fields = ["symbol", "status", "error", "candles", "data_start", "data_end", "available_days"]

    metrics_path = os.path.join(ROOT, args.save_metrics)
    diagnostics_path = os.path.join(ROOT, args.save_diagnostics)
    report_path = os.path.join(ROOT, args.save_report)
    metrics = []
    diagnostics = []
    done = set()
    if args.resume and os.path.exists(metrics_path):
        metrics = read_csv(metrics_path)
        done = {row["symbol"] for row in metrics}
    if args.resume and os.path.exists(diagnostics_path):
        diagnostics = read_csv(diagnostics_path)

    for index, source_row in enumerate(source_rows, start=1):
        spec = spec_from_row(source_row)
        symbol = spec["symbol"]
        if symbol in done:
            print(f"[{index}/{len(source_rows)}] {symbol} skipped resume", flush=True)
            continue

        print(
            f"[{index}/{len(source_rows)}] {symbol} {spec['direction']} "
            f"th{spec['threshold']} {spec['regime']} TP {spec['tp_pct'] * 100:.2f}% "
            f"T{spec['time_stop_min']}",
            flush=True,
        )
        try:
            started = time.perf_counter()
            candles, _, _ = fetch_klines_bounded(multi, symbol, max_days, args.warmup_days, first_days.get(symbol))
            fetch_seconds = time.perf_counter() - started
            if len(candles) < 30 * 1440:
                raise RuntimeError(f"not enough candles for 30d: {len(candles)}")
            base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
            indicator_started = time.perf_counter()
            bt.add_indicators_and_signals(candles, base_args)
            indicator_seconds = time.perf_counter() - indicator_started
            data_start = candles[0]["open_time"]
            data_end = candles[-1]["close_time"]
            available_days = len(candles) / 1440.0
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "ok",
                    "error": "",
                    "candles": len(candles),
                    "data_start": data_start,
                    "data_end": data_end,
                    "available_days": f"{available_days:.2f}",
                }
            )
            for period in args.windows:
                for scenario in SCENARIOS:
                    result = run_one_window(bt, reinvest, multi, cf, candles, spec, period, scenario)
                    metrics.append(
                        metric_row(source_row, spec, period, scenario, result, data_start, data_end, f"{available_days:.2f}")
                    )
            strict30 = best_metric(metrics, symbol, "strict_maker", 30)
            strict365 = best_metric(metrics, symbol, "strict_maker", 365)
            print(
                "  strict30="
                + (fmt_pct(strict30["return_pct"]) if strict30 else "n/a")
                + " strict365="
                + (fmt_pct(strict365["return_pct"]) if strict365 else "n/a"),
                flush=True,
            )
            print(
                f"  candles={len(candles)} fetch={fetch_seconds:.1f}s indicators={indicator_seconds:.1f}s",
                flush=True,
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "error",
                    "error": str(exc),
                    "candles": "",
                    "data_start": "",
                    "data_end": "",
                    "available_days": "",
                }
            )
            print(f"  error: {exc}", flush=True)

        save_csv(metrics_path, metrics, metric_fields)
        save_csv(diagnostics_path, diagnostics, diagnostics_fields)
        save_report(report_path, source_rows, metrics, diagnostics, args.windows)

    save_csv(metrics_path, metrics, metric_fields)
    save_csv(diagnostics_path, diagnostics, diagnostics_fields)
    save_report(report_path, source_rows, metrics, diagnostics, args.windows)
    print(f"saved metrics: {metrics_path}")
    print(f"saved diagnostics: {diagnostics_path}")
    print(f"saved report: {report_path}")


if __name__ == "__main__":
    main()
