#!/usr/bin/env python3
"""Daily fixed check for the strict multi-window survivor strategies.

These variants were selected on 2026-05-07 because they stayed positive on
1d/7d/30d/60d with maker-limit strict entry offset 0.05%. This script does not
optimize anything; it re-runs the exact fixed variants on fresh data.
"""

import argparse
import csv
import importlib.util
import math
import os
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")
TWEAK_PATH = os.path.join(ROOT, "scripts", "shortlist_24h_tweak_search.py")


STRICT_SURVIVORS = [
    {
        "coin": "CHZ",
        "symbol": "CHZUSDT",
        "strategy": "CHZ LONG strict",
        "kind": "single",
        "direction": "long",
        "threshold": 60,
        "atr_min": 0.0025,
        "dist_abs_max": 0.025,
        "ret_min": -0.40,
        "ret_max": 0.10,
        "tp_pct": 0.0050,
        "time_stop_min": 90,
        "limit_offset": 0.0005,
    },
    {
        "coin": "ANKR",
        "symbol": "ANKRUSDT",
        "strategy": "ANKR LONG strict",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "atr_min": 0.0,
        "dist_abs_max": 0.025,
        "ret_min": -0.20,
        "ret_max": 0.05,
        "tp_pct": 0.0100,
        "time_stop_min": 60,
        "limit_offset": 0.0005,
    },
    {
        "coin": "GALA",
        "symbol": "GALAUSDT",
        "strategy": "GALA 7.3 strict",
        "kind": "gala_73",
        "direction": "short",
        "threshold": 40,
        "atr_min": 0.0025,
        "dist_abs_max": None,
        "ret_min": 0.0,
        "ret_max": 0.25,
        "tp_pct": 0.0028,
        "time_stop_min": 30,
        "limit_offset": 0.0005,
    },
    {
        "coin": "GALA",
        "symbol": "GALAUSDT",
        "strategy": "GALA 11.2 strict",
        "kind": "gala_112",
        "short_threshold": 60,
        "long_threshold": 50,
        "atr_min": 0.0025,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "short_tp_pct": 0.0028,
        "long_tp_pct": 0.0025,
        "time_stop_min": 90,
        "short_weight": 1.35,
        "long_weight": 0.0,
        "limit_offset": 0.0005,
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


def fmt_pf(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def fetch_candles(bt, reinvest, multi, tweak, symbol, max_days, warmup_days, market):
    _full, run = tweak.fetch_candles(bt, reinvest, multi, symbol, max_days, warmup_days, market)
    return run


def slice_period(bt, candles, days):
    bars = days * bt.candles_per_day("1m")
    if len(candles) < bars:
        raise RuntimeError(f"not enough candles for {days}d")
    return candles[-bars:]


def spec_by_coin(cf, coin):
    for spec in cf.BEST_SPECS:
        if spec.get("coin") == coin and spec.get("kind") == "single":
            row = dict(spec)
            row["kind"] = "single"
            return row
    raise RuntimeError(f"single spec not found: {coin}")


def variant_for_tweak(variant):
    row = dict(variant)
    row.setdefault("limit_timeout", 1)
    row.setdefault("fee_pct", 0.0002)
    row.setdefault("slippage_pct", 0.0)
    if row["kind"] == "gala_112":
        row["short_ret_min"] = row["ret_min"]
        row["short_ret_max"] = row["ret_max"]
        row["long_ret_min"] = row["ret_min"]
        row["long_ret_max"] = row["ret_max"]
    return row


def run_variant(tweak, bt, reinvest, multi, cf, paper, candles, variant):
    v = variant_for_tweak(variant)
    if v["kind"] == "single":
        return tweak.run_single(
            bt,
            reinvest,
            multi,
            cf,
            paper,
            candles,
            spec_by_coin(cf, v["coin"]),
            v,
            v["strategy"],
        )
    if v["kind"] == "gala_73":
        spec = {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_73", "direction": "short"}
        return tweak.run_single(bt, reinvest, multi, cf, paper, candles, spec, v, v["strategy"])
    if v["kind"] == "gala_112":
        return tweak.run_gala_112(bt, reinvest, multi, paper, candles, v)
    raise ValueError(v["kind"])


def verdict(period_rows, min_pf, min_trades_1d):
    failed = []
    for row in period_rows:
        days = int(row["days"])
        min_trades = min_trades_1d if days <= 1 else max(3, min_trades_1d * 2)
        if days >= 30:
            min_trades = max(8, min_trades_1d * 4)
        if row["accepted"] < min_trades:
            failed.append(f"{days}d trades {row['accepted']} < {min_trades}")
        if row["return_sum_pct"] <= 0:
            failed.append(f"{days}d return {fmt_pct(row['return_sum_pct'])} <= 0")
        if row["profit_factor"] < min_pf:
            failed.append(f"{days}d PF {fmt_pf(row['profit_factor'])} < {min_pf:.2f}")
    return ("PASS", "") if not failed else ("WATCH", "; ".join(failed))


def write_report(path, rows, summary_path, diagnostics_path, generated_at):
    periods = sorted({int(row["days"]) for row in rows})
    grouped = {}
    for row in rows:
        grouped.setdefault((row["coin"], row["strategy"]), {})[int(row["days"])] = row

    lines = [
        "# Daily Strict Survivor Check",
        "",
        f"Generated: {generated_at}",
        "",
        "Ежедневная проверка 4 strict-стратегий, зафиксированных 2026-05-07.",
        "Параметры не оптимизируются заново.",
        "",
        "| Coin | Strategy | Status | " + " | ".join(f"{period}d Return / PF / Trades" for period in periods) + " | Reason |",
        "|---|---|---|" + "|".join("---:" for _ in periods) + "|---|",
    ]
    for key, period_map in sorted(grouped.items()):
        status = next(iter(period_map.values())).get("status", "")
        reason = next(iter(period_map.values())).get("status_reason", "")
        metrics = []
        for period in periods:
            row = period_map.get(period, {})
            metrics.append(
                f"{fmt_pct(row.get('return_sum_pct'))} / "
                f"{fmt_pf(row.get('profit_factor'))} / "
                f"{row.get('accepted', '')}"
            )
        lines.append(f"| {key[0]} | {key[1]} | {status} | " + " | ".join(metrics) + f" | {reason} |")
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
            f"- Diagnostics CSV: `{diagnostics_path}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Daily check for fixed strict survivor strategies.")
    parser.add_argument("--market", choices=["data_api_spot", "futures_archive"], default="data_api_spot")
    parser.add_argument("--periods", nargs="*", type=int, default=[1, 7, 30, 60])
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--min-pf", type=float, default=1.01)
    parser.add_argument("--min-trades-1d", type=int, default=1)
    parser.add_argument("--save-summary", default=f"data/daily_strict_survivor_check_{today}.csv")
    parser.add_argument("--save-diagnostics", default=f"data/daily_strict_survivor_check_diagnostics_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/daily-strict-survivor-check-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    tweak = load_module("shortlist_24h_tweak_search", TWEAK_PATH)

    max_days = max(args.periods)
    candles_cache = {}
    diagnostics = []
    rows = []

    for variant in STRICT_SURVIVORS:
        symbol = variant["symbol"]
        try:
            if symbol not in candles_cache:
                candles_cache[symbol] = fetch_candles(bt, reinvest, multi, tweak, symbol, max_days, args.warmup_days, args.market)
                candles = candles_cache[symbol]
                diagnostics.append(
                    {
                        "symbol": symbol,
                        "status": "ok",
                        "candles": len(candles),
                        "start": candles[0]["open_time"],
                        "end": candles[-1]["close_time"],
                        "error": "",
                    }
                )
            period_rows = []
            for days in sorted(args.periods):
                run_candles = slice_period(bt, candles_cache[symbol], days)
                journal = run_variant(tweak, bt, reinvest, multi, cf, paper, run_candles, variant)
                summary = tweak.summarize(journal)
                row = {
                    **summary,
                    "coin": variant["coin"],
                    "symbol": symbol,
                    "strategy": variant["strategy"],
                    "days": days,
                    "market": args.market,
                    "data_start": run_candles[0]["open_time"],
                    "data_end": run_candles[-1]["close_time"],
                }
                period_rows.append(row)
            status, reason = verdict(period_rows, args.min_pf, args.min_trades_1d)
            for row in period_rows:
                row["status"] = status
                row["status_reason"] = reason
                rows.append(row)
            print(f"{variant['strategy']}: {status} {reason}", flush=True)
        except Exception as exc:
            diagnostics.append({"symbol": symbol, "status": "error", "candles": "", "start": "", "end": "", "error": str(exc)})

    fields = [
        "coin",
        "symbol",
        "strategy",
        "status",
        "status_reason",
        "days",
        "market",
        "data_start",
        "data_end",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
    ]
    diagnostic_fields = ["symbol", "status", "candles", "start", "end", "error"]
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields)
    save_csv(os.path.join(ROOT, args.save_diagnostics), diagnostics, diagnostic_fields)
    write_report(args.save_report, rows, args.save_summary, args.save_diagnostics, datetime.now(timezone.utc).isoformat())
    print(f"saved summary: {args.save_summary}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
