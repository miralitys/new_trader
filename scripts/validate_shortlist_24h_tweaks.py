#!/usr/bin/env python3
"""Validate the 24h-overfit shortlist tweaks on longer windows.

The input settings come from `shortlist_24h_tweak_search.py`. This script does
not search again; it runs those exact variants on 7/30/60d so we can see which
ones survive outside the fitted 24h window.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")


FIXED_VARIANTS = [
    {
        "coin": "CHZ",
        "symbol": "CHZUSDT",
        "strategy": "CHZ LONG 24h tweak",
        "kind": "single",
        "direction": "long",
        "threshold": 60,
        "atr_min": 0.0,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "tp_pct": 0.0100,
        "time_stop_min": 60,
        "limit_offset": 0.0,
    },
    {
        "coin": "ANKR",
        "symbol": "ANKRUSDT",
        "strategy": "ANKR LONG 24h tweak",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "atr_min": 0.0,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "tp_pct": 0.0100,
        "time_stop_min": 30,
        "limit_offset": 0.0,
    },
    {
        "coin": "MANA",
        "symbol": "MANAUSDT",
        "strategy": "MANA LONG 24h tweak",
        "kind": "single",
        "direction": "long",
        "threshold": 80,
        "atr_min": 0.0,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "tp_pct": 0.0100,
        "time_stop_min": 60,
        "limit_offset": 0.0,
    },
    {
        "coin": "SPELL",
        "symbol": "SPELLUSDT",
        "strategy": "SPELL SHORT 24h tweak",
        "kind": "single",
        "direction": "short",
        "threshold": 70,
        "atr_min": 0.0,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "tp_pct": 0.0050,
        "time_stop_min": 180,
        "limit_offset": 0.0,
    },
    {
        "coin": "GALA",
        "symbol": "GALAUSDT",
        "strategy": "GALA 7.3 protected 24h tweak",
        "kind": "gala_73",
        "direction": "short",
        "threshold": 60,
        "atr_min": 0.0,
        "dist_abs_max": None,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "tp_pct": 0.0050,
        "time_stop_min": 60,
        "limit_offset": 0.0,
    },
    {
        "coin": "GALA",
        "symbol": "GALAUSDT",
        "strategy": "GALA 11.2 watchlist 24h tweak",
        "kind": "gala_112",
        "short_threshold": 999,
        "long_threshold": 50,
        "atr_min": 0.0025,
        "dist_abs_max": 0.025,
        "ret_min": -0.50,
        "ret_max": 0.25,
        "short_tp_pct": 0.0028,
        "long_tp_pct": 0.0050,
        "time_stop_min": 30,
        "short_weight": 0.0,
        "long_weight": 0.9,
        "limit_offset": 0.0,
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
    return f"{float(value):+.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market):
    if market == "futures_archive":
        candles, _, _ = multi.fetch_klines_fast(symbol, days, warmup_days)
    else:
        candles = bt.fetch_klines(market, symbol, days + warmup_days, "1m")
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    bars = days * bt.candles_per_day("1m")
    return candles[-bars:]


def apply_custom_signals(rows, direction, threshold, atr_min, dist_abs_max, ret_min, ret_max):
    for row in rows:
        passed = (
            in_range(row.get("atr_pct"), atr_min, None)
            and (dist_abs_max is None or in_range(row.get("dist_ema200"), -dist_abs_max, dist_abs_max))
            and in_range(row.get("return_7d"), ret_min, ret_max)
        )
        row["long_signal"] = False
        row["short_signal"] = False
        if direction == "long":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= threshold
                and bool(row.get("smart_long_filter"))
                and passed
            )
        else:
            row["short_signal"] = row.get("short_score", 0.0) >= threshold and passed


def apply_execution(paper, args, direction, tp_pct, time_stop_min, limit_offset, fee_pct):
    paper.apply_execution(
        args,
        entry_mode="maker_limit",
        fee_pct=fee_pct,
        slippage_pct=0.0,
        limit_offset=limit_offset,
        timeout_min=1,
    )
    args.time_stop_min = time_stop_min
    if direction == "long":
        args.long_time_stop_min = time_stop_min
        args.long_tp_pct = tp_pct
    else:
        args.short_time_stop_min = time_stop_min
        args.short_tp_pct = tp_pct


def summarize(rows):
    accepted = [row for row in rows if row.get("portfolio_status") == "accepted"]
    filled = [row for row in rows if row.get("order_status") == "filled"]
    unfilled = [row for row in rows if row.get("order_status") == "unfilled"]
    skipped_overlap = [row for row in rows if row.get("portfolio_status") == "skipped_overlap"]
    returns = [
        float(row["portfolio_return_pct"])
        for row in accepted
        if row.get("portfolio_return_pct") not in ("", None)
    ]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    total = sum(returns)
    return {
        "signals": len(rows),
        "filled": len(filled),
        "unfilled": len(unfilled),
        "accepted": len(accepted),
        "skipped_overlap": len(skipped_overlap),
        "return_sum_pct": total,
        "profit_factor": gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0),
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "expectancy_pct": total / len(accepted) if accepted else 0.0,
        "exit_reasons": ";".join(
            f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted).items() if key
        ),
    }


def run_single(bt, reinvest, multi, cf, paper, candles, variant, fee_pct):
    rows = [dict(row) for row in candles]
    apply_custom_signals(
        rows,
        variant["direction"],
        variant["threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["ret_min"],
        variant["ret_max"],
    )
    if variant["kind"] == "single":
        template = next(spec for spec in cf.BEST_SPECS if spec.get("coin") == variant["coin"] and spec["kind"] == "single")
        args = cf.make_single_args(multi, reinvest, template)
    else:
        args = multi.make_strategy_args(reinvest, "7.3", variant["symbol"])
    apply_execution(
        paper,
        args,
        variant["direction"],
        variant["tp_pct"],
        variant["time_stop_min"],
        variant["limit_offset"],
        fee_pct,
    )
    return paper.journal_loop(
        bt,
        rows,
        args,
        {
            "asset": variant["coin"],
            "symbol": variant["symbol"],
            "strategy": variant["strategy"],
            "module": "fixed_24h_tweak",
        },
    )


def run_gala_112(bt, reinvest, multi, paper, candles, variant, fee_pct):
    all_rows = []

    short_rows = [dict(row) for row in candles]
    apply_custom_signals(
        short_rows,
        "short",
        variant["short_threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["ret_min"],
        variant["ret_max"],
    )
    short_args = multi.make_strategy_args(reinvest, "7.3", "GALAUSDT")
    apply_execution(
        paper,
        short_args,
        "short",
        variant["short_tp_pct"],
        variant["time_stop_min"],
        variant["limit_offset"],
        fee_pct,
    )
    all_rows.extend(
        paper.journal_loop(
            bt,
            short_rows,
            short_args,
            {"asset": "GALA", "symbol": "GALAUSDT", "strategy": variant["strategy"], "module": "short_sleeve"},
            portfolio_weight=variant["short_weight"],
        )
    )

    long_rows = [dict(row) for row in candles]
    apply_custom_signals(
        long_rows,
        "long",
        variant["long_threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["ret_min"],
        variant["ret_max"],
    )
    long_args = multi.make_strategy_args(reinvest, "10", "GALAUSDT")
    apply_execution(
        paper,
        long_args,
        "long",
        variant["long_tp_pct"],
        variant["time_stop_min"],
        variant["limit_offset"],
        fee_pct,
    )
    all_rows.extend(
        paper.journal_loop(
            bt,
            long_rows,
            long_args,
            {"asset": "GALA", "symbol": "GALAUSDT", "strategy": variant["strategy"], "module": "long_sleeve"},
            portfolio_weight=variant["long_weight"],
        )
    )

    open_until = None
    for row in sorted(all_rows, key=lambda item: (paper.parse_time(item["order_start_time"]), item["module"])):
        if row["order_status"] != "filled":
            row["portfolio_status"] = "unfilled"
            continue
        entry_time = paper.parse_time(row["fill_time"])
        if open_until is not None and entry_time < open_until:
            row["portfolio_status"] = "skipped_overlap"
            continue
        row["portfolio_status"] = "accepted"
        open_until = paper.parse_time(row["exit_time"])
    return all_rows


def write_report(path, rows, summary_path):
    periods = sorted({int(row["days"]) for row in rows})
    lines = [
        "# Validate Shortlist 24h Tweaks",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Проверка берет настройки, найденные на последних 24 часах, и прогоняет их без нового подбора на длинных окнах.",
        "",
        "| Coin | Strategy | " + " | ".join(f"{period}d Return" for period in periods) + " | Verdict |",
        "|---|---|" + "|".join("---:" for _ in periods) + "|---|",
    ]
    grouped = {}
    for row in rows:
        grouped.setdefault((row["coin"], row["strategy"]), {})[int(row["days"])] = row
    for key, item in sorted(grouped.items()):
        returns = [item.get(period, {}).get("return_sum_pct", "") for period in periods]
        positive = sum(1 for value in returns if value != "" and float(value) > 0)
        verdict = "survived" if positive == len(periods) else ("mixed" if positive else "failed")
        lines.append(
            f"| {key[0]} | {key[1]} | "
            + " | ".join(fmt_pct(value) if value != "" else "n/a" for value in returns)
            + f" | {verdict} |"
        )
    lines.extend(["", "## Files", "", f"- Summary CSV: `{summary_path}`"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["data_api_spot", "futures_archive"], default="data_api_spot")
    parser.add_argument("--periods", nargs="*", type=int, default=[7, 30, 60])
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--save-summary", default="data/validate_shortlist_24h_tweaks_summary.csv")
    parser.add_argument("--save-report", default="strategies/validate-shortlist-24h-tweaks.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)

    rows = []
    cache = {}
    for days in args.periods:
        for variant in FIXED_VARIANTS:
            key = (variant["symbol"], days)
            if key not in cache:
                cache[key] = fetch_candles(bt, reinvest, multi, variant["symbol"], days, args.warmup_days, args.market)
            candles = cache[key]
            if variant["kind"] == "gala_112":
                journal = run_gala_112(bt, reinvest, multi, paper, candles, variant, args.fee_pct)
            else:
                journal = run_single(bt, reinvest, multi, cf, paper, candles, variant, args.fee_pct)
            summary = summarize(journal)
            summary.update(
                {
                    "coin": variant["coin"],
                    "symbol": variant["symbol"],
                    "strategy": variant["strategy"],
                    "days": days,
                    "market": args.market,
                    "data_start": candles[0]["open_time"],
                    "data_end": candles[-1]["close_time"],
                }
            )
            rows.append(summary)
            print(
                f"{days}d {variant['coin']} {variant['strategy']}: "
                f"{fmt_pct(summary['return_sum_pct'])} PF={fmt_pf(summary['profit_factor'])} "
                f"accepted={summary['accepted']}",
                flush=True,
            )

    fields = [
        "coin",
        "symbol",
        "strategy",
        "days",
        "market",
        "data_start",
        "data_end",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "skipped_overlap",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
    ]
    save_csv(args.save_summary, rows, fields)
    write_report(args.save_report, rows, args.save_summary)
    print(f"report: {args.save_report}")


if __name__ == "__main__":
    main()
