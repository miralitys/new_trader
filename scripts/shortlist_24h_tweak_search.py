#!/usr/bin/env python3
"""Deliberately overfit the current shortlist on the last 24h.

This script is diagnostic only. It searches a broad but still interpretable set
of parameter tweaks for the current shortlist and reports whether each strategy
can be made positive on the latest rolling 24h paper execution.
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
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")


SHORTLIST = [
    {"coin": "CHZ", "symbol": "CHZUSDT", "kind": "single"},
    {"coin": "ANKR", "symbol": "ANKRUSDT", "kind": "single"},
    {"coin": "MANA", "symbol": "MANAUSDT", "kind": "single"},
    {"coin": "SPELL", "symbol": "SPELLUSDT", "kind": "single"},
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_73"},
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
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
    return candles, candles[-bars:]


def spec_by_coin(cf, coin):
    for spec in cf.BEST_SPECS:
        if spec.get("coin") == coin and spec.get("kind") == "single":
            return dict(spec)
    raise RuntimeError(f"single spec not found: {coin}")


def apply_custom_single_signals(rows, direction, threshold, atr_min, dist_abs_max, ret_min, ret_max):
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


def apply_execution(paper, args, variant):
    paper.apply_execution(
        args,
        entry_mode="maker_limit",
        fee_pct=variant["fee_pct"],
        slippage_pct=variant["slippage_pct"],
        limit_offset=variant["limit_offset"],
        timeout_min=variant["limit_timeout"],
    )
    args.time_stop_min = variant["time_stop_min"]
    if variant["direction"] == "long":
        args.long_time_stop_min = variant["time_stop_min"]
        args.long_tp_pct = variant["tp_pct"]
    else:
        args.short_time_stop_min = variant["time_stop_min"]
        args.short_tp_pct = variant["tp_pct"]
    return args


def summarize(rows):
    accepted = [row for row in rows if row.get("portfolio_status") == "accepted"]
    filled = [row for row in rows if row.get("order_status") == "filled"]
    unfilled = [row for row in rows if row.get("order_status") == "unfilled"]
    returns = [float(row["portfolio_return_pct"]) for row in accepted if row.get("portfolio_return_pct") not in ("", None)]
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
        "return_sum_pct": total,
        "profit_factor": gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0),
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "expectancy_pct": total / len(accepted) if accepted else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted).items() if key),
    }


def single_variants(base_spec):
    direction = base_spec["direction"]
    base_tp = base_spec["tp_pct"]
    threshold_values = sorted(set([base_spec["threshold"], 50, 60, 70, 80]))
    if direction == "long":
        tp_values = sorted(set([0.0025, 0.005, base_tp, 0.010]))
    else:
        tp_values = sorted(set([0.0025, 0.005, base_tp, 0.010]))
    base_ret = (0.20 if base_spec["regime"] == "wide" else 0.10)
    base_time = base_spec["time_stop_min"]
    for threshold in threshold_values:
        for atr_min in [0.0, 0.0025]:
            for dist_abs_max in [0.025, None]:
                for ret_min, ret_max in [(-0.50, 0.25), (-0.40, base_ret), (-0.20, 0.05), (0.0, 0.25)]:
                    for tp_pct in tp_values:
                        for time_stop_min in sorted(set([30, 60, base_time])):
                            for limit_offset in [0.0, 0.0005]:
                                yield {
                                    "direction": direction,
                                    "threshold": threshold,
                                    "atr_min": atr_min,
                                    "dist_abs_max": dist_abs_max,
                                    "ret_min": ret_min,
                                    "ret_max": ret_max,
                                    "tp_pct": tp_pct,
                                    "time_stop_min": time_stop_min,
                                    "limit_offset": limit_offset,
                                    "limit_timeout": 1,
                                    "fee_pct": 0.0002,
                                    "slippage_pct": 0.0,
                                }


def gala_73_variants():
    for threshold in [40, 50, 60, 70, 80]:
        for atr_min in [0.0, 0.0025]:
            for dist_abs_max in [0.025, None]:
                for ret_min, ret_max in [(-0.50, 0.25), (-0.40, 0.10), (-0.20, 0.05), (0.0, 0.25)]:
                    for tp_pct in [0.0025, 0.0028, 0.004, 0.005]:
                        for time_stop_min in [30, 60, 120]:
                            for limit_offset in [0.0, 0.0005]:
                                yield {
                                    "direction": "short",
                                    "threshold": threshold,
                                    "atr_min": atr_min,
                                    "dist_abs_max": dist_abs_max,
                                    "ret_min": ret_min,
                                    "ret_max": ret_max,
                                    "tp_pct": tp_pct,
                                    "time_stop_min": time_stop_min,
                                    "limit_offset": limit_offset,
                                    "limit_timeout": 1,
                                    "fee_pct": 0.0002,
                                    "slippage_pct": 0.0,
                                }


def variant_name(v):
    dist = "any" if v["dist_abs_max"] is None else f"{v['dist_abs_max']:.3f}"
    return (
        f"thr{v['threshold']} atr>={v['atr_min']:.4f} dist<={dist} "
        f"ret7 {v['ret_min']:.2f}..{v['ret_max']:.2f} tp{v['tp_pct']:.4f} "
        f"T{v['time_stop_min']} off{v['limit_offset']:.4f}"
    )


def run_single(bt, reinvest, multi, cf, paper, candles, spec, variant, strategy_name):
    rows = [dict(row) for row in candles]
    apply_custom_single_signals(
        rows,
        spec["direction"],
        variant["threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["ret_min"],
        variant["ret_max"],
    )
    args = cf.make_single_args(multi, reinvest, spec) if spec.get("kind") == "single" else multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
    apply_execution(paper, args, variant)
    return paper.journal_loop(
        bt,
        rows,
        args,
        {"asset": spec["coin"], "symbol": spec["symbol"], "strategy": strategy_name, "module": variant_name(variant)},
    )


def run_gala_112(bt, reinvest, multi, paper, candles, variant):
    all_rows = []

    short_rows = [dict(row) for row in candles]
    apply_custom_single_signals(
        short_rows,
        "short",
        variant["short_threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["short_ret_min"],
        variant["short_ret_max"],
    )
    short_args = multi.make_strategy_args(reinvest, "7.3", "GALAUSDT")
    short_v = dict(variant)
    short_v["direction"] = "short"
    short_v["threshold"] = variant["short_threshold"]
    short_v["ret_min"] = variant["short_ret_min"]
    short_v["ret_max"] = variant["short_ret_max"]
    short_v["tp_pct"] = variant["short_tp_pct"]
    apply_execution(paper, short_args, short_v)
    all_rows.extend(
        paper.journal_loop(
            bt,
            short_rows,
            short_args,
            {"asset": "GALA", "symbol": "GALAUSDT", "strategy": "GALA 11.2 overfit", "module": variant_name(short_v) + " short"},
            portfolio_weight=variant["short_weight"],
        )
    )

    long_rows = [dict(row) for row in candles]
    apply_custom_single_signals(
        long_rows,
        "long",
        variant["long_threshold"],
        variant["atr_min"],
        variant["dist_abs_max"],
        variant["long_ret_min"],
        variant["long_ret_max"],
    )
    long_args = multi.make_strategy_args(reinvest, "10", "GALAUSDT")
    long_v = dict(variant)
    long_v["direction"] = "long"
    long_v["threshold"] = variant["long_threshold"]
    long_v["ret_min"] = variant["long_ret_min"]
    long_v["ret_max"] = variant["long_ret_max"]
    long_v["tp_pct"] = variant["long_tp_pct"]
    apply_execution(paper, long_args, long_v)
    all_rows.extend(
        paper.journal_loop(
            bt,
            long_rows,
            long_args,
            {"asset": "GALA", "symbol": "GALAUSDT", "strategy": "GALA 11.2 overfit", "module": variant_name(long_v) + " long"},
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


def gala_112_variants():
    for short_threshold in [40, 60, 80, 999]:
        for long_threshold in [50, 70, 999]:
            if short_threshold == 999 and long_threshold == 999:
                continue
            for ret_min, ret_max in [(-0.50, 0.25), (-0.40, 0.10), (-0.20, 0.05)]:
                for tp_short in [0.0028, 0.004]:
                    for tp_long in [0.0025, 0.005]:
                        for time_stop_min in [30, 60, 90]:
                            for short_weight in [0.0, 0.9, 1.35]:
                                for long_weight in [0.0, 0.9]:
                                    if short_weight == 0 and long_weight == 0:
                                        continue
                                    for limit_offset in [0.0, 0.0005]:
                                        yield {
                                            "short_threshold": short_threshold,
                                            "long_threshold": long_threshold,
                                            "atr_min": 0.0025,
                                            "dist_abs_max": 0.025,
                                            "short_ret_min": ret_min,
                                            "short_ret_max": ret_max,
                                            "long_ret_min": ret_min,
                                            "long_ret_max": ret_max,
                                            "short_tp_pct": tp_short,
                                            "long_tp_pct": tp_long,
                                            "time_stop_min": time_stop_min,
                                            "limit_offset": limit_offset,
                                            "limit_timeout": 1,
                                            "fee_pct": 0.0002,
                                            "slippage_pct": 0.0,
                                            "short_weight": short_weight,
                                            "long_weight": long_weight,
                                        }


def gala_112_name(v):
    return (
        f"S{v['short_threshold']} L{v['long_threshold']} ret7 {v['short_ret_min']:.2f}..{v['short_ret_max']:.2f} "
        f"tpS{v['short_tp_pct']:.4f} tpL{v['long_tp_pct']:.4f} T{v['time_stop_min']} "
        f"wS{v['short_weight']:.2f} wL{v['long_weight']:.2f} off{v['limit_offset']:.4f}"
    )


def choose_best(candidates, min_accepted=1):
    viable = [row for row in candidates if row["accepted"] >= min_accepted]
    if not viable:
        viable = candidates
    return sorted(
        viable,
        key=lambda row: (
            row["return_sum_pct"],
            row["profit_factor"] if not math.isinf(row["profit_factor"]) else 999.0,
            row["accepted"],
        ),
        reverse=True,
    )[0]


def write_report(path, rows, diagnostics, summary_path):
    lines = [
        "# Shortlist 24h Tweak Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Внимание: это намеренная подгонка под последние 24 часа. Использовать только как список гипотез для проверки на 7/30/60 дней.",
        "",
        "| Coin | Strategy | Best 24h Variant | Accepted | Return | PF | Win | Verdict |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['coin']} | {row['strategy']} | {row['variant']} | {row['accepted']} | "
            f"{fmt_pct(row['return_sum_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{float(row['win_rate_pct']):.2f}% | {row['verdict']} |"
        )
    lines.extend(["", "## Diagnostics", "", "| Symbol | Status | Error |", "|---|---|---|"])
    for row in diagnostics:
        lines.append(f"| {row['symbol']} | {row['status']} | {row.get('error', '')} |")
    lines.extend(["", "## Files", "", f"- Summary CSV: `{summary_path}`"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["data_api_spot", "futures_archive"], default="data_api_spot")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--save-summary", default="data/shortlist_24h_tweak_summary.csv")
    parser.add_argument("--save-report", default="strategies/shortlist-24h-tweak-search.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)

    cache = {}
    diagnostics = []
    best_rows = []

    for item in SHORTLIST:
        symbol = item["symbol"]
        print(f"search {item['coin']} {item['kind']} {symbol}", flush=True)
        try:
            if symbol not in cache:
                _full, run = fetch_candles(bt, reinvest, multi, symbol, args.days, args.warmup_days, args.market)
                cache[symbol] = run
                diagnostics.append({"symbol": symbol, "status": "ok", "error": "", "candles": len(run), "start": run[0]["open_time"], "end": run[-1]["close_time"]})
            candles = cache[symbol]
            candidates = []
            if item["kind"] == "single":
                spec = spec_by_coin(cf, item["coin"])
                spec["kind"] = "single"
                for variant in single_variants(spec):
                    journal = run_single(bt, reinvest, multi, cf, paper, candles, spec, variant, f"{item['coin']} {spec['direction'].upper()} overfit")
                    summary = summarize(journal)
                    summary.update({"coin": item["coin"], "symbol": symbol, "strategy": f"{item['coin']} {spec['direction'].upper()} Best", "variant": variant_name(variant)})
                    candidates.append(summary)
            elif item["kind"] == "gala_73":
                spec = {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_73", "direction": "short"}
                for variant in gala_73_variants():
                    journal = run_single(bt, reinvest, multi, cf, paper, candles, spec, variant, "GALA 7.3 overfit")
                    summary = summarize(journal)
                    summary.update({"coin": "GALA", "symbol": symbol, "strategy": "GALA 7.3 protected", "variant": variant_name(variant)})
                    candidates.append(summary)
            elif item["kind"] == "gala_112":
                for variant in gala_112_variants():
                    journal = run_gala_112(bt, reinvest, multi, paper, candles, variant)
                    summary = summarize(journal)
                    summary.update({"coin": "GALA", "symbol": symbol, "strategy": "GALA 11.2 watchlist", "variant": gala_112_name(variant)})
                    candidates.append(summary)
            else:
                raise ValueError(item["kind"])
            best = choose_best(candidates, min_accepted=1)
            best["verdict"] = "positive_overfit" if best["accepted"] > 0 and best["return_sum_pct"] > 0 else "no_positive_trade_found"
            best_rows.append(best)
        except Exception as exc:
            diagnostics.append({"symbol": symbol, "status": "error", "error": str(exc), "candles": "", "start": "", "end": ""})

    fields = [
        "coin",
        "symbol",
        "strategy",
        "variant",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
        "verdict",
    ]
    save_csv(args.save_summary, best_rows, fields)
    write_report(args.save_report, best_rows, diagnostics, args.save_summary)
    for row in best_rows:
        print(
            f"{row['coin']} {row['strategy']}: {row['variant']} "
            f"accepted={row['accepted']} return={fmt_pct(row['return_sum_pct'])} "
            f"PF={fmt_pf(row['profit_factor'])} {row['verdict']}"
        )


if __name__ == "__main__":
    main()
